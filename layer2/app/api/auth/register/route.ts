import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { username, password } = await request.json();

    // Forward the request to your FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!backendUrl) {
      throw new Error("Backend API URL is not configured");
    }

    const res = await fetch(`${backendUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      // Forward the error from the backend
      return NextResponse.json(
        { success: false, detail: data.detail || "Registration failed on backend" },
        { status: res.status }
      );
    }

    return NextResponse.json({ success: true, ...data });

  } catch (error) {
    console.error("Frontend registration API error:", error);
    const message = error instanceof Error ? error.message : "An unexpected error occurred";
    return NextResponse.json(
      { success: false, detail: message },
      { status: 500 }
    );
  }
}
