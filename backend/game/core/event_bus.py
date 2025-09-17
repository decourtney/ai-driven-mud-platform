from typing import Callable, Dict, Any, List, Coroutine
import asyncio


# async event bus
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[..., Coroutine]]] = {}

    def subscribe(self, event_name: str, handler: Callable[..., Coroutine]):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)

    async def emit(self, event_name: str, *args, **kwargs):
        if event_name not in self._subscribers:
            return
        # fire all listeners concurrently
        await asyncio.gather(
            *(handler(*args, **kwargs) for handler in self._subscribers[event_name])
        )
