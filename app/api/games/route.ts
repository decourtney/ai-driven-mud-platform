import { NextResponse } from "next/server";
import axios from "axios"

const backendUrl = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await axios.get(`${backendUrl}/games`); // FastAPI endpoint
    return NextResponse.json(res.data);
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      { error: "Failed to fetch games" },
      { status: 500 }
    );
  }
}
