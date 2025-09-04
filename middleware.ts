import NextAuth from "next-auth";
import authConfig from "./auth.config";
import { NextRequest } from "next/server";

const { auth } = NextAuth(authConfig);
export default auth(async function middleware(req: NextRequest) {
  // custom middleware logic goes here
});
