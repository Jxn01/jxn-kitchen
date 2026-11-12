"""The FastAPI application: API under /api, the built web app at / (when a static dir is configured)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr
from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import asyncio
import logging
import hashlib
import json

from . import __version__, blends, catalogue, cooktimers, db, folders, gluten, kiosk, knowhow, pantry, recipes, references, settings, shopping
from . import sauce_data, sauce_engine, sauces, spice_data, spice_engine
from .ingredients import format_qty, parse_line
from .matcher import Matcher
from .config import Config
from . import images, importer, scans
from .events import Broadcaster, sse_stream
from .ha import HAClient
from .weather import WeatherService


log = logging.getLogger(__name__)


class PantryWrite(BaseModel):
    have: StrictBool


class RecipeIn(BaseModel):
    title: StrictStr = Field(min_length=1, max_length=200)
    servings: StrictInt = Field(4, ge=1, le=50)
    prep_min: StrictInt | None = Field(None, ge=0, le=10000)
    cook_min: StrictInt | None = Field(None, ge=0, le=10000)
    total_min: StrictInt | None = Field(None, ge=0, le=10000)
    ingredients: list[Annotated[StrictStr, Field(max_length=400)]] = Field(default_factory=list, max_length=200)
    steps: list[Annotated[StrictStr, Field(max_length=4000)]] = Field(default_factory=list, max_length=100)
    tags: list[Annotated[StrictStr, Field(max_length=40)]] = Field(default_factory=list, max_length=20)
    notes: StrictStr | None = Field(None, max_length=10000)
    source_url: StrictStr | None = Field(None, max_length=2000)
    lang: Literal['hu', 'en'] | None = None
    folder_id: StrictInt | None = None      # POST only: file the new recipe there (unknown -> top level). PUT ignores it.


class FolderIn(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=folders.MAX_NAME)
    parent_id: StrictInt | None = None


class FolderPatch(BaseModel):
    name: StrictStr | None = Field(None, min_length=1, max_length=folders.MAX_NAME)
    parent_id: StrictInt | None = None      # only applied when SENT: null = the top level, absent = stays put


class RecipeMove(BaseModel):
    ids: list[StrictInt] = Field(min_length=1, max_length=500)
    folder_id: StrictInt | None             # null = the top level


class BlendPart(BaseModel):
    spice: StrictStr = Field(min_length=1, max_length=64)
    parts: float = Field(gt=0, le=1000)


class BlendIn(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]*$')
    notes: StrictStr | None = Field(None, max_length=4000)
    tags: list[Annotated[StrictStr, Field(max_length=40)]] = Field(default_factory=list, max_length=20)
    parts: list[BlendPart] = Field(min_length=1, max_length=spice_engine.MAX_SPICES)
    lang: Literal['hu', 'en'] | None = None


class BlendEvaluate(BaseModel):
    parts: list[BlendPart] = Field(min_length=1, max_length=spice_engine.MAX_SPICES)
    batch_tbsp: float | None = Field(None, gt=0, le=1000)
    seq: StrictInt | None = None


class SauceLine(BaseModel):
    """One line of a sauce: a shelf item, a rack jar, a blend, a typed line matched to a catalogue item, or raw text."""
    shelf: StrictStr | None = Field(None, max_length=64)
    spice: StrictStr | None = Field(None, max_length=64)
    blend: StrictInt | None = None
    item: StrictStr | None = Field(None, max_length=64)
    raw: StrictStr | None = Field(None, max_length=200, pattern=r'^[^\x00-\x1f\x7f]*$')
    qty: float | None = Field(None, gt=0, le=5000)
    unit: Literal['tbsp', 'tsp', 'ml', 'dl', 'g', 'pcs'] | None = None
    ok_gf: StrictBool = False
    match_how: Literal['exact', 'stem', 'fuzzy'] | None = None


class SauceIn(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]*$')
    notes: StrictStr | None = Field(None, max_length=4000)
    tags: list[Annotated[StrictStr, Field(max_length=40)]] = Field(default_factory=list, max_length=20)
    yield_ml: StrictInt | None = Field(None, ge=10, le=5000)
    family: StrictStr | None = Field(None, max_length=40)
    lines: list[SauceLine] = Field(min_length=1, max_length=sauce_engine.MAX_LINES)
    steps: list[Annotated[StrictStr, Field(max_length=2000)]] = Field(default_factory=list, max_length=30)
    lang: Literal['hu', 'en'] | None = None


class SauceEvaluate(BaseModel):
    lines: list[SauceLine] = Field(min_length=1, max_length=sauce_engine.MAX_LINES)
    steps: list[Annotated[StrictStr, Field(max_length=2000)]] = Field(default_factory=list, max_length=30)
    family: StrictStr | None = Field(None, max_length=40)
    seq: StrictInt | None = None


class TypedLine(BaseModel):
    text: StrictStr = Field(min_length=1, max_length=200, pattern=r'^[^\x00-\x1f\x7f]*$')


class TimerIn(BaseModel):
    label: StrictStr = Field('', max_length=60, pattern=r'^[^\x00-\x1f\x7f]*$')   # no control chars (log/notification)
    seconds: StrictInt = Field(ge=1, le=86400)
    recipe_id: StrictInt | None = None
    step_pos: StrictInt | None = Field(None, ge=0, le=1000)


class TimerAct(BaseModel):
    action: Literal['pause', 'resume', 'add', 'dismiss']
    seconds: StrictInt = Field(60, ge=1, le=3600)


class ImportIn(BaseModel):
    url: StrictStr = Field(max_length=2000)


class LineFix(BaseModel):
    item_id: StrictStr | None = None
    ok_gf: StrictBool = False


class ParseIn(BaseModel):
    lines: list[Annotated[StrictStr, Field(max_length=400)]] = Field(max_length=200)


class ShoppingAdd(BaseModel):
    text: StrictStr | None = Field(None, max_length=200)
    item_id: StrictStr | None = Field(None, max_length=100)


class ShoppingPatch(BaseModel):
    done: StrictBool | None = None
    text: StrictStr | None = Field(None, max_length=200)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_app(cfg: Config, *, http: httpx.AsyncClient | None = None,
               now: Callable[[], datetime] | None = None, shopping_sync_every: float | None = 20.0,
               resolver: importer.Resolver | None = None, timers_autorun: bool = True,
               scans_autorun: bool = True) -> FastAPI:
    resolve = resolver or importer.default_resolver
    now = now or _utcnow

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cat = catalogue.load(cfg.catalogue_path)
        errors = catalogue.validate(cat)
        if errors:
            raise RuntimeError('invalid catalogue: ' + '; '.join(errors[:10]))
        app.state.catalogue = cat
        app.state.matcher = Matcher(cat)
        app.state.match_index = catalogue.match_index(cat)
        body = json.dumps(catalogue.to_json(cat), ensure_ascii=False, separators=(',', ':')).encode()
        app.state.catalogue_json = body
        app.state.catalogue_etag = '"' + hashlib.sha256(body).hexdigest()[:16] + '"'
        lib = knowhow.load(cfg.knowhow_path)
        kh_errors = knowhow.validate(lib)
        if kh_errors:                                  # like the catalogue: never ship a half-translated library
            raise RuntimeError('invalid know-how library: ' + '; '.join(kh_errors[:10]))
        app.state.knowhow_json = json.dumps(knowhow.to_json(lib), ensure_ascii=False, separators=(',', ':')).encode()
        app.state.knowhow_etag = '"' + hashlib.sha256(app.state.knowhow_json).hexdigest()[:16] + '"'
        app.state.spices = None
        app.state.sauces = None
        if cfg.spices:
            spices = spice_data.load(cfg.engine_path / 'spices')
            sp_errors = spice_data.validate(spices, cat)
            if sp_errors:                              # one bad cell and the server does not start 
                raise RuntimeError(f'invalid spice knowledge ({len(sp_errors)} errors): ' + '; '.join(sp_errors[:10]))
            app.state.spices = spice_engine.SpiceEngine(spices, cat)
            app.state.rack_json = json.dumps(blends.rack(app.state.spices, cat, lib), ensure_ascii=False,
                                             separators=(',', ':')).encode()
            app.state.rack_etag = '"' + hashlib.sha256(app.state.rack_json).hexdigest()[:16] + '"'
            sd = sauce_data.load(cfg.engine_path / 'sauces')
            sd_errors = sauce_data.validate(sd, cat, spices)
            if sd_errors:                              # the same rule for the sauce knowledge
                raise RuntimeError(f'invalid sauce knowledge ({len(sd_errors)} errors): ' + '; '.join(sd_errors[:10]))
            app.state.sauces = sauce_engine.SauceEngine(sd, app.state.spices, cat)
            app.state.shelves_json = json.dumps(sauces.shelves(app.state.sauces, cat), ensure_ascii=False,
                                                separators=(',', ':')).encode()
            app.state.shelves_etag = '"' + hashlib.sha256(app.state.shelves_json).hexdigest()[:16] + '"'
        app.state.db = db.connect(cfg.db_path)
        if app.state.spices and (n := blends.seed(app.state.db, app.state.spices.data, now())):
            log.info('seeded %d classic blends', n)
        if app.state.sauces and (n := sauces.seed(app.state.db, app.state.sauces.data, now())):
            log.info('seeded %d classic sauces', n)
        if n := references.migrate(app.state.db, cat):
            log.warning('rewrote %d stored catalogue ids through replaced.yaml', n)
        if n := recipes.rematch_all(app.state.db, app.state.matcher):
            log.info('re-matched %d recipe lines against the current catalogue', n)
        client = http or httpx.AsyncClient()
        app.state.ha = HAClient(cfg.ha_url, cfg.ha_token, client)
        app.state.weather = WeatherService(app.state.ha, cfg.weather_entity, now)
        app.state.dangling = references.dangling(app.state.db, cat)
        if app.state.dangling:
            log.error('stored ids missing from the catalogue (add them to catalogue/replaced.yaml): %r',
                      app.state.dangling[:20])
        app.state.shopping_sync = shopping.ShoppingSync(app.state.ha, app.state.db, app.state.events, now)
        task = asyncio.create_task(app.state.shopping_sync.run(shopping_sync_every)) if shopping_sync_every else None
        app.state.timers = cooktimers.TimerService(app.state.db, app.state.events, app.state.ha, now,
                                                   lambda: settings.get_all(app.state.db)['language'])
        timer_task = asyncio.create_task(app.state.timers.run()) if timers_autorun else None
        app.state.scans = scans.Scanner(app.state.db, app.state.matcher, cfg.data_dir, now,
                                        lambda rid: app.state.events.publish('recipes', {'id': rid}), cfg.scans_dir)
        scan_task = asyncio.create_task(app.state.scans.run()) if scans_autorun and cfg.scans_dir else None
        yield
        for t in (task, timer_task, scan_task):
            if t:
                t.cancel()
        if http is None:
            await client.aclose()
        app.state.db.close()

    app = FastAPI(title='JXN Kitchen', version=__version__, lifespan=lifespan)
    app.state.cfg = cfg
    app.state.events = Broadcaster()
    app.state.kiosk = kiosk.KioskState(now)

    @app.get('/api/health')
    async def health() -> JSONResponse:
        # a stored id the catalogue no longer has fails LOUDLY — Gatus goes red, deploy.sh reports it —
        # while the app keeps serving (such a reference only stops matching; it never invents a match)
        body = {'ok': not app.state.dangling, 'version': __version__, 'build': cfg.build}
        if app.state.dangling:
            body['dangling'] = app.state.dangling
        return JSONResponse(body, status_code=200 if body['ok'] else 503)

    @app.get('/api/settings')
    async def get_settings() -> dict[str, Any]:
        return settings.get_all(app.state.db)

    @app.put('/api/settings')
    async def put_settings(patch: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            result = settings.update(app.state.db, patch)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        app.state.events.publish('settings', result)
        return result

    @app.get('/api/events')
    async def events(request: Request) -> StreamingResponse:
        return StreamingResponse(sse_stream(app.state.events, request.is_disconnected),
                                 media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.get('/api/catalogue')
    async def get_catalogue(request: Request) -> Response:
        etag = app.state.catalogue_etag
        if request.headers.get('if-none-match') == etag:
            return Response(status_code=304, headers={'ETag': etag})
        return Response(app.state.catalogue_json, media_type='application/json',
                        headers={'ETag': etag, 'Cache-Control': 'no-cache'})

    @app.get('/api/knowhow')
    async def get_knowhow(request: Request) -> Response:
        if request.headers.get('if-none-match') == app.state.knowhow_etag:
            return Response(status_code=304, headers={'ETag': app.state.knowhow_etag})
        return Response(app.state.knowhow_json, media_type='application/json', headers={'ETag': app.state.knowhow_etag})

    @app.get('/api/pantry')
    async def get_pantry() -> dict[str, Any]:
        return pantry.get_state(app.state.db, app.state.catalogue)

    @app.put('/api/pantry/{node:path}')
    async def put_pantry(node: str, body: PantryWrite) -> dict[str, Any]:
        try:
            state = pantry.set_node(app.state.db, app.state.catalogue, node, body.have, now())
        except pantry.UnknownNode:
            raise HTTPException(status_code=404, detail=f'unknown pantry node: {node}')
        except pantry.HiddenItem:
            raise HTTPException(status_code=422, detail=f'not a pantry item: {node}')
        app.state.events.publish('pantry', {'node': node, 'have': body.have, 'state': state})
        return state

    background: set[asyncio.Task] = set()      # keep references: an unreferenced task can be garbage-collected

    def nudge_sync() -> None:
        if shopping_sync_every:
            task = asyncio.get_running_loop().create_task(app.state.shopping_sync.round())
            background.add(task)
            task.add_done_callback(_finished)

    def _finished(task: asyncio.Task) -> None:
        background.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error('shopping sync nudge failed', exc_info=task.exception())

    def shopping_changed() -> list[dict[str, Any]]:
        items = shopping.list_items(app.state.db)
        app.state.events.publish('shopping', {'items': items})
        return items

    @app.get('/api/shopping')
    async def get_shopping() -> list[dict[str, Any]]:
        return shopping.list_items(app.state.db)

    @app.post('/api/shopping')
    async def post_shopping(body: ShoppingAdd) -> dict[str, Any]:
        lang = settings.get_all(app.state.db)['language']
        try:
            text, item_id = shopping.entry(app.state.catalogue, app.state.match_index, lang, body.text, body.item_id)
        except shopping.NotFound:
            raise HTTPException(status_code=404, detail=f'unknown item: {body.item_id}')
        except shopping.BadText as e:
            raise HTTPException(status_code=422, detail=str(e))
        item = shopping.add(app.state.db, text, item_id, now())
        shopping_changed()
        nudge_sync()
        return item

    @app.patch('/api/shopping/{item_id}')
    async def patch_shopping(item_id: int, body: ShoppingPatch) -> dict[str, Any]:
        try:
            item = shopping.update(app.state.db, item_id, now(), done=body.done, text=body.text)
        except shopping.NotFound:
            raise HTTPException(status_code=404, detail='no such item')
        except shopping.BadText as e:
            raise HTTPException(status_code=422, detail=str(e))
        shopping_changed()
        nudge_sync()
        return item

    @app.delete('/api/shopping/{item_id}', status_code=204)
    async def delete_shopping(item_id: int) -> Response:
        try:
            shopping.delete(app.state.db, item_id, now())
        except shopping.NotFound:
            raise HTTPException(status_code=404, detail='no such item')
        shopping_changed()
        nudge_sync()
        return Response(status_code=204)

    @app.post('/api/shopping/clear-done')
    async def clear_done() -> list[dict[str, Any]]:
        shopping.clear_done(app.state.db, now())
        nudge_sync()
        return shopping_changed()

    # --- recipes ---------------------------------------------------------------------------------------------
    def lang_now() -> str:
        return settings.get_all(app.state.db)['language']

    def pantry_state() -> dict[str, Any]:
        return pantry.get_state(app.state.db, app.state.catalogue)

    def recipe_changed(rid: int) -> None:
        app.state.events.publish('recipes', {'id': rid})

    @app.get('/api/recipes')
    async def list_recipes(q: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
        return recipes.summaries(app.state.db, app.state.catalogue, pantry_state(), lang_now(), q, tag)

    @app.get('/api/cookable')
    async def cookable() -> list[dict[str, Any]]:
        return recipes.cookable(app.state.db, app.state.catalogue, pantry_state(), lang_now())

    # --- recipe folders (folders.py) --------------------------------------------------------------------------
    def folders_changed() -> None:
        app.state.events.publish('recipes', {'folders': True})   # one event: every screen reloads recipes + folders

    def folder_error(e: Exception) -> HTTPException:
        if isinstance(e, folders.NotFound):
            return HTTPException(status_code=404, detail='no such folder')
        assert isinstance(e, folders.Invalid)
        return HTTPException(status_code=422 if e.code == 'name' else 409, detail={'code': e.code, 'message': str(e)})

    @app.get('/api/folders')
    async def list_folders() -> list[dict[str, Any]]:
        return folders.list_all(app.state.db)

    @app.post('/api/folders')
    async def create_folder(body: FolderIn) -> dict[str, Any]:
        try:
            fid = folders.create(app.state.db, body.name, body.parent_id, now())
        except (folders.NotFound, folders.Invalid) as e:
            raise folder_error(e)
        folders_changed()
        return folders.get(app.state.db, fid)

    @app.patch('/api/folders/{fid}')
    async def patch_folder(fid: int, body: FolderPatch) -> dict[str, Any]:
        kw: dict[str, Any] = {}
        if 'name' in body.model_fields_set and body.name is not None:
            kw['name'] = body.name
        if 'parent_id' in body.model_fields_set:
            kw['parent_id'] = body.parent_id
        try:
            folders.update(app.state.db, fid, now(), **kw)
        except (folders.NotFound, folders.Invalid) as e:
            raise folder_error(e)
        folders_changed()
        return folders.get(app.state.db, fid)

    @app.delete('/api/folders/{fid}')
    async def delete_folder(fid: int) -> dict[str, int]:
        try:
            moved = folders.delete(app.state.db, fid, now())
        except folders.NotFound as e:
            raise folder_error(e)
        folders_changed()
        return moved

    @app.post('/api/recipes/move')
    async def move_recipes(body: RecipeMove) -> dict[str, int]:
        try:
            n = folders.move_recipes(app.state.db, body.ids, body.folder_id)
        except folders.NotFound as e:
            raise HTTPException(status_code=404, detail=f'no such folder or recipe: {e.args[0]}')
        folders_changed()
        return {'moved': n}

    @app.get('/api/recipes/{rid}')
    async def get_recipe(rid: int, servings: int | None = None) -> dict[str, Any]:
        if servings is not None and not 1 <= servings <= 100:
            raise HTTPException(status_code=422, detail='servings out of range')
        try:
            return recipes.get(app.state.db, app.state.catalogue, pantry_state(), rid, lang_now(), servings)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe')

    @app.post('/api/recipes')
    async def create_recipe(body: RecipeIn) -> dict[str, Any]:
        rid = recipes.save(app.state.db, app.state.matcher, body.model_dump(), now())
        if body.folder_id is not None and folders.exists(app.state.db, body.folder_id):
            folders.move_recipes(app.state.db, [rid], body.folder_id)   # a folder deleted meanwhile: top level
        recipe_changed(rid)
        return {'id': rid}

    @app.put('/api/recipes/{rid}')
    async def update_recipe(rid: int, body: RecipeIn) -> dict[str, Any]:
        try:
            recipes.save(app.state.db, app.state.matcher, body.model_dump(), now(), rid)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe')
        recipe_changed(rid)
        return recipes.get(app.state.db, app.state.catalogue, pantry_state(), rid, lang_now())

    @app.delete('/api/recipes/{rid}', status_code=204)
    async def delete_recipe(rid: int) -> Response:
        try:
            image = recipes.delete(app.state.db, rid)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe')
        if image:
            (cfg.data_dir / 'images' / image).unlink(missing_ok=True)
        recipe_changed(rid)
        return Response(status_code=204)

    @app.put('/api/recipes/{rid}/lines/{pos}')
    async def fix_line(rid: int, pos: int, body: LineFix) -> dict[str, Any]:
        try:
            recipes.set_line(app.state.db, app.state.catalogue, rid, pos, body.item_id, body.ok_gf)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe, line or item')
        recipe_changed(rid)
        return recipes.get(app.state.db, app.state.catalogue, pantry_state(), rid, lang_now())

    @app.post('/api/recipes/{rid}/missing-to-shopping')
    async def missing_to_shopping(rid: int) -> list[dict[str, Any]]:
        try:
            ids = recipes.missing_items(app.state.db, app.state.catalogue, pantry_state(), rid)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe')
        lang = lang_now()
        added = [shopping.add(app.state.db, *shopping.entry(app.state.catalogue, app.state.match_index, lang, None, i),
                              now()) for i in ids]
        shopping_changed()
        nudge_sync()
        return added

    @app.put('/api/recipes/{rid}/image')
    async def put_image(rid: int, request: Request) -> dict[str, Any]:
        limit = 15 * 1024 * 1024
        if int(request.headers.get('content-length') or 0) > limit:
            raise HTTPException(status_code=413, detail='image too large (15 MB max)')
        buf = bytearray()
        async for chunk in request.stream():                  # never hold more than the cap in memory
            buf += chunk
            if len(buf) > limit:
                raise HTTPException(status_code=413, detail='image too large (15 MB max)')
        data = bytes(buf)
        if not data:
            raise HTTPException(status_code=422, detail='no image sent')
        try:
            recipes.get_row(app.state.db, rid)
        except recipes.NotFound:
            raise HTTPException(status_code=404, detail='no such recipe')
        try:
            name = await asyncio.to_thread(images.store, cfg.data_dir / 'images', rid, data)
        except images.BadImage as e:
            raise HTTPException(status_code=422, detail=str(e))
        old = app.state.db.execute('SELECT image FROM recipe WHERE id = ?', (rid,)).fetchone()['image']
        recipes.set_image(app.state.db, rid, name)
        if old and old != name:
            (cfg.data_dir / 'images' / old).unlink(missing_ok=True)
        recipe_changed(rid)
        return {'image': f'/api/images/{name}'}

    @app.get('/api/images/{name}')
    async def get_image(name: str) -> Response:
        if not images.SAFE_NAME.fullmatch(name):
            raise HTTPException(status_code=404)
        path = cfg.data_dir / 'images' / name
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'public, max-age=31536000, immutable'})

    @app.post('/api/import')
    async def import_url(body: ImportIn) -> dict[str, Any]:
        try:
            url = importer.check_url(body.url, resolve)
        except importer.ImportRefused as e:
            raise HTTPException(status_code=422, detail={'message': str(e), 'code': e.code})
        reason, code, data, html = None, None, None, ''
        try:
            url, raw, _ = await importer.fetch(app.state.ha.http, url, resolve)
            html = raw.decode('utf-8', errors='replace')
            data = importer.extract(html, url)
            if not data['ingredients']:
                reason, code = 'no recipe found on that page', 'no_recipe'
        except (importer.FetchFailed, importer.ImportRefused) as e:
            reason, code = str(e), e.code
        except Exception as e:                              # a scraper bug must not lose the link
            reason, code = f'could not read the recipe ({type(e).__name__})', 'scraper'
        site = (importer.urlsplit(url).hostname or '').removeprefix('www.')
        if reason:
            title = importer.page_title(html) or site or 'Recipe'
            rid = recipes.save(app.state.db, app.state.matcher,
                               {'title': title, 'source_url': url, 'source_site': site, 'notes': f'Import: {reason}',
                                'origin': 'url', 'ingredients': [], 'steps': []}, now())
            recipe_changed(rid)
            return {'id': rid, 'draft': True, 'reason': reason, 'code': code}
        rid = recipes.save(app.state.db, app.state.matcher,
                           {'title': data['title'], 'source_url': url, 'source_site': data['site'], 'origin': 'url',
                            'servings': data['servings'] or 4, 'total_min': data['total_min'],
                            'prep_min': data['prep_min'], 'cook_min': data['cook_min'],
                            'ingredients': data['ingredients'], 'steps': data['steps']}, now())
        if data['image_url']:
            try:
                _, img, _ = await importer.fetch(app.state.ha.http, data['image_url'], resolve,
                                                 limit=importer.MAX_IMAGE, accept='image/*')
                name = await asyncio.to_thread(images.store, cfg.data_dir / 'images', rid, img)
                recipes.set_image(app.state.db, rid, name)
            except Exception:
                pass                                          # a recipe without its photo is still a recipe
        recipe_changed(rid)
        return {'id': rid, 'draft': False}

    # --- spice blends ---------------------------------------------------------------------
    def blend_changed(bid: int) -> None:
        app.state.events.publish('blends', {'id': bid})

    @app.middleware('http')
    async def spices_off(request: Request, call_next):
        if app.state.spices is None and request.url.path.startswith(('/api/spices', '/api/blends', '/api/sauces')):
            return JSONResponse({'detail': 'the spice engine is switched off'}, status_code=503)
        return await call_next(request)

    def check_parts(parts: list[BlendPart]) -> list[tuple[str, float]]:
        ps = [(p.spice, p.parts) for p in parts]
        try:
            app.state.spices._check(ps)
        except spice_engine.EngineInputError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return ps

    @app.get('/api/spices')
    async def get_rack(request: Request) -> Response:
        if request.headers.get('if-none-match') == app.state.rack_etag:
            return Response(status_code=304, headers={'ETag': app.state.rack_etag})
        return Response(app.state.rack_json, media_type='application/json', headers={'ETag': app.state.rack_etag})

    @app.post('/api/blends/evaluate')
    async def evaluate_blend(body: BlendEvaluate) -> dict[str, Any]:
        ps = check_parts(body.parts)
        out = app.state.spices.evaluate(ps, body.batch_tbsp)
        out['gluten'] = blends.gluten_line(app.state.spices, app.state.catalogue, pantry_state(), [s for s, _ in ps])
        out['seq'] = body.seq
        return out

    @app.get('/api/blends')
    async def list_blends(q: str | None = None) -> list[dict[str, Any]]:
        return blends.summaries(app.state.db, app.state.spices, app.state.catalogue, pantry_state(), q)

    @app.get('/api/blends/{bid}')
    async def get_blend(bid: int, batch_tbsp: float | None = None) -> dict[str, Any]:
        if batch_tbsp is not None and not 0 < batch_tbsp <= 1000:
            raise HTTPException(status_code=422, detail='batch_tbsp out of range')
        try:
            return blends.get(app.state.db, app.state.spices, app.state.catalogue, pantry_state(), bid, batch_tbsp)
        except blends.NotFound:
            raise HTTPException(status_code=404, detail='no such blend')

    @app.post('/api/blends')
    async def create_blend(body: BlendIn) -> dict[str, Any]:
        check_parts(body.parts)
        bid = blends.save(app.state.db, body.model_dump(), now())
        blend_changed(bid)
        return {'id': bid}

    @app.put('/api/blends/{bid}')
    async def update_blend(bid: int, body: BlendIn) -> dict[str, Any]:
        check_parts(body.parts)
        try:
            blends.save(app.state.db, body.model_dump(), now(), bid)
        except blends.NotFound:
            raise HTTPException(status_code=404, detail='no such blend')
        blend_changed(bid)
        return blends.get(app.state.db, app.state.spices, app.state.catalogue, pantry_state(), bid)

    @app.delete('/api/blends/{bid}', status_code=204)
    async def delete_blend(bid: int) -> Response:
        try:
            blends.delete(app.state.db, bid)
        except blends.NotFound:
            raise HTTPException(status_code=404, detail='no such blend')
        except blends.InUse as e:
            raise HTTPException(status_code=409, detail={'message': 'a sauce uses this blend', 'sauces': e.sauces})
        blend_changed(bid)
        return Response(status_code=204)

    @app.post('/api/blends/{bid}/riff')
    async def riff_blend(bid: int) -> dict[str, Any]:
        try:
            new = blends.riff(app.state.db, app.state.spices.data, bid, lang_now(), now())
        except blends.NotFound:
            raise HTTPException(status_code=404, detail='no such blend')
        blend_changed(new)
        return {'id': new}

    # --- sauces -------------------------------------------------------------------------------
    def sauce_changed(sid: int) -> None:
        app.state.events.publish('sauces', {'id': sid})

    def rack_ids() -> dict[str, dict[str, Any]]:
        return app.state.spices.p

    def stored_lines(lines: list[SauceLine]) -> list[dict[str, Any]]:
        try:
            return sauces.check_lines(app.state.db, app.state.sauces.data, set(rack_ids()), app.state.catalogue,
                                      [ln.model_dump() for ln in lines])
        except sauces.BadLine as e:
            raise HTTPException(status_code=422, detail=str(e))

    def check_family(fam: str | None) -> None:
        if fam is not None and app.state.sauces.data.family(fam) is None:
            raise HTTPException(status_code=422, detail=f'{fam} is not a sauce family')

    def evaluate_stored(stored: list[dict[str, Any]], steps: list[str], fam: str | None) -> dict[str, Any] | None:
        try:
            return app.state.sauces.evaluate(sauces.engine_lines(app.state.db, stored, lang_now(), app.state.spices.data),
                                             steps, fam)
        except sauce_engine.SauceInputError as e:
            raise HTTPException(status_code=422, detail=str(e))

    @app.get('/api/sauces/shelves')
    async def get_shelves(request: Request) -> Response:
        if request.headers.get('if-none-match') == app.state.shelves_etag:
            return Response(status_code=304, headers={'ETag': app.state.shelves_etag})
        return Response(app.state.shelves_json, media_type='application/json', headers={'ETag': app.state.shelves_etag})

    @app.post('/api/sauces/evaluate')
    async def evaluate_sauce(body: SauceEvaluate) -> dict[str, Any]:
        check_family(body.family)
        stored = stored_lines(body.lines)
        out = evaluate_stored(stored, body.steps, body.family)
        out['gluten'] = sauces.gluten_lines(app.state.db, app.state.sauces, app.state.catalogue, pantry_state(), stored, lang_now())
        out['seq'] = body.seq
        return out

    @app.post('/api/sauces/line')
    async def type_sauce_line(body: TypedLine) -> dict[str, Any]:
        try:
            return sauces.typed(app.state.matcher, app.state.sauces.data, rack_ids(), body.text)
        except sauces.BadLine as e:
            raise HTTPException(status_code=422, detail=str(e))

    @app.get('/api/sauces')
    async def list_sauces(q: str | None = None) -> list[dict[str, Any]]:
        return sauces.summaries(app.state.db, app.state.sauces, app.state.catalogue, pantry_state(), q, lang_now())

    @app.get('/api/sauces/{sid}')
    async def get_sauce(sid: int) -> dict[str, Any]:
        try:
            return sauces.get(app.state.db, app.state.sauces, app.state.catalogue, pantry_state(), sid, lang_now())
        except sauces.NotFound:
            raise HTTPException(status_code=404, detail='no such sauce')

    @app.post('/api/sauces')
    async def create_sauce(body: SauceIn) -> dict[str, Any]:
        check_family(body.family)
        stored = stored_lines(body.lines)
        sid = sauces.save(app.state.db, body.model_dump(), stored, now())
        sauce_changed(sid)
        return {'id': sid}

    @app.put('/api/sauces/{sid}')
    async def update_sauce(sid: int, body: SauceIn) -> dict[str, Any]:
        check_family(body.family)
        stored = stored_lines(body.lines)
        try:
            sauces.save(app.state.db, body.model_dump(), stored, now(), sid)
        except sauces.NotFound:
            raise HTTPException(status_code=404, detail='no such sauce')
        sauce_changed(sid)
        return sauces.get(app.state.db, app.state.sauces, app.state.catalogue, pantry_state(), sid, lang_now())

    @app.delete('/api/sauces/{sid}', status_code=204)
    async def delete_sauce(sid: int) -> Response:
        try:
            sauces.delete(app.state.db, sid)
        except sauces.NotFound:
            raise HTTPException(status_code=404, detail='no such sauce')
        sauce_changed(sid)
        return Response(status_code=204)

    @app.post('/api/sauces/{sid}/riff')
    async def riff_sauce(sid: int) -> dict[str, Any]:
        try:
            new = sauces.riff(app.state.db, app.state.sauces.data, sid, lang_now(), now())
        except sauces.NotFound:
            raise HTTPException(status_code=404, detail='no such sauce')
        sauce_changed(new)
        return {'id': new}

    # --- digitising ------------------------------------------------------------------------------
    @app.post('/api/scan')
    async def post_scan(request: Request) -> dict[str, Any]:
        limit = scans.MAX_BYTES
        if int(request.headers.get('content-length') or 0) > limit:
            raise HTTPException(status_code=413, detail='too large')
        buf = bytearray()
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > limit:
                raise HTTPException(status_code=413, detail='too large')
        try:
            ids = await app.state.scans.import_bytes(bytes(buf), 'photo')
        except scans.NotAScan as e:
            raise HTTPException(status_code=422, detail=str(e))
        return {'ids': ids}

    @app.get('/api/scans')
    async def scans_status() -> dict[str, Any]:
        return app.state.scans.status()

    # --- kitchen timers ------------------------------------------------------------------------------
    @app.get('/api/timers')
    async def get_timers() -> list[dict[str, Any]]:
        return cooktimers.list_active(app.state.db, now())

    @app.post('/api/timers')
    async def post_timer(body: TimerIn) -> dict[str, Any]:
        t = cooktimers.create(app.state.db, now(), body.label, body.seconds, body.recipe_id, body.step_pos)
        app.state.timers.changed()
        return t

    @app.patch('/api/timers/{tid}')
    async def patch_timer(tid: int, body: TimerAct) -> dict[str, Any]:
        try:
            t = cooktimers.act(app.state.db, now(), tid, body.action, body.seconds)
        except cooktimers.NotFound:
            raise HTTPException(status_code=404, detail='no such timer')
        app.state.timers.changed()
        return t

    @app.delete('/api/timers/{tid}', status_code=204)
    async def delete_timer(tid: int) -> Response:
        try:
            cooktimers.delete(app.state.db, tid)
        except cooktimers.NotFound:
            raise HTTPException(status_code=404, detail='no such timer')
        app.state.timers.changed()
        return Response(status_code=204)

    @app.post('/api/parse')
    async def parse_preview(body: ParseIn) -> list[dict[str, Any]]:
        # the preview reads like the saved recipe will: in the recipe's (guessed) language, not the UI's
        cat, st = app.state.catalogue, pantry_state()
        lang = recipes.guess_lang(*body.lines)
        out = []
        for raw in body.lines:
            for p in parse_line(raw):
                m = app.state.matcher.match(p.name, unit=p.unit, qty=p.qty)
                item = cat.items.get(m.item_id or '')
                out.append({'raw': raw, 'name': p.name, 'qty_text': format_qty(p.qty, p.unit, lang, p.qty_max),
                            'item_id': m.item_id, 'how': m.how,
                            'item_name': (item.hu if lang == 'hu' else item.en) if item else None,
                            'gluten': gluten.check_line(cat, st, m.item_id, False).status,
                            'gf_name': gluten.gf_name(cat, m.item_id, lang)})
        return out

    @app.get('/api/weather')
    async def weather() -> dict[str, Any]:
        return await app.state.weather.current()

    @app.post('/api/kiosk/heartbeat', status_code=204)
    async def heartbeat(hb: kiosk.Heartbeat) -> Response:
        app.state.kiosk.beat(hb)
        return Response(status_code=204)

    @app.get('/api/kiosk/health')
    async def kiosk_health() -> JSONResponse:
        ok, body = app.state.kiosk.health()
        return JSONResponse(body, status_code=200 if ok else 503)

    @app.get('/api/kiosk/display')
    async def kiosk_display() -> dict[str, Any]:
        return kiosk.display(now(), cfg.timezone, settings.get_all(app.state.db))

    @app.middleware('http')
    async def cors_for_the_overlay(request: Request, call_next):
        # the Browse overlay runs on third-party sites and loads our font from here (font loads are CORS requests);
        # the agent fetches /overlay.js itself. Nothing else is shared cross-origin.
        response = await call_next(request)
        if request.url.path.startswith('/fonts/') or request.url.path == '/overlay.js':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    if cfg.static_dir is not None:
        app.mount('/', WebFiles(directory=cfg.static_dir, html=True), name='web')
    return app


class WebFiles(StaticFiles):
    """The built web app, with a cache rule for every file BY CONSTRUCTION.

    Vite content-hashes ``/assets/*``: a name there never changes meaning, so it is cached for a year. Everything else
    keeps its name across builds (``/``, ``sw.js``, ``sw-strategy.js``, ``sprite.svg``, fonts, icons) and must
    revalidate every time (``no-cache``; its ETag makes that a 304). Without a ``Cache-Control`` header Chrome guesses
    a freshness of 10 % of the file's age: the kiosk reused a stale copy of ``sw-strategy.js`` for hours, the new service
    worker's import of it failed, and the kiosk stayed on the old worker after a deploy.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code < 400:
            hashed = path.replace('\\', '/').lstrip('./').startswith('assets/')
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if hashed else 'no-cache'
        return response
