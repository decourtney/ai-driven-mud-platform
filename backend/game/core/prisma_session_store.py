from prisma import Prisma
import asyncio

class PrismaSessionStore:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def save(self, session_id: str, data: dict):
        await self.prisma.game_session.upsert(
            where={"id": session_id},
            update={
                "sceneState": data["scene_state"],
                "turnNumber": data.get("turn_number", 0),
                "isActive": data.get("is_active", True),
            },
            create={
                "id": session_id,
                "userId": data["user_id"],
                "slug": data["slug"],
                "playerSetup": data["player_setup"],
                "sceneState": data["scene_state"],
                "turnNumber": data.get("turn_number", 0),
                "isActive": data.get("is_active", True),
            }
        )

    async def load(self, session_id: str):
        record = await self.prisma.game_session.find_unique(where={"id": session_id})
        if not record:
            return None
        return {
            "id": record.id,
            "user_id": record.userId,
            "slug": record.slug,
            "player_setup": record.playerSetup,
            "scene_state": record.sceneState,
            "turn_number": record.turnNumber,
            "is_active": record.isActive
        }

    async def delete(self, session_id: str):
        await self.prisma.game_session.delete(where={"id": session_id})
