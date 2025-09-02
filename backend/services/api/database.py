from prisma import Prisma

# Global prisma instance
prisma = Prisma()

async def connect_db():
    """Connect to the database"""
    await prisma.connect()
    print("[PRISMA] Connected to database")

async def disconnect_db():
    """Disconnect from the database"""
    await prisma.disconnect()
    print("[PRISMA] Disconnected from database")