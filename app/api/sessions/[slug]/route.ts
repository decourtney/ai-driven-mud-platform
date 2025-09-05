import { auth } from "@/auth";
import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BASE_URL ||
  "http://localhost:5432/mudai_dev?schema=public";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const {slug} = await params
  const session = await auth(); // server-side auth

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await req.json();
    console.log({ ...body, userId: session.user.id, slug: slug });

    // Add the userId from auth to send to backend
    const res = await fetch(
      `${BACKEND_URL}/sessions/${slug}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_state: {...body}, user_id: session.user.id, slug: slug }),
      }
    );

    if (!res.ok) {
      const errorText = await res.text();
      console.log(errorText);
      return NextResponse.json(
        { error: errorText },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || "Failed to create session" },
      { status: 500 }
    );
  }
}
