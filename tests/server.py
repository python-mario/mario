import asyncio

from aiohttp import web
import attr


@attr.s
class Handler:

    counter = attr.ib(default=0)

    async def handle(self, request):
        name = request.match_info.get("name", "Anonymous")
        text = f"Hello, {name}. You are client number {self.counter} for this server."
        await asyncio.sleep(2)
        self.counter += 1
        return web.Response(text=text)


app = web.Application()
handler = Handler()
handle = handler.handle
app.add_routes([web.get("/", handle), web.get("/{name}", handle)])

web.run_app(app)
