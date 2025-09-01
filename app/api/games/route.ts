import { NextResponse } from "next/server";

const backendUrl = process.env.DATABASE_URL || "http://localhost:8000";

export async function GET() {
  const res = await fetch(`${backendUrl}/games`);

  if (!res.ok) {
    return NextResponse.json(
      { error: "Failed to fetch games" },
      { status: res.status }
    );
  }

  const games = await res.json();
  return NextResponse.json(games);
}
