import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    localPatterns: [
      {
        pathname: "/assets/images/**",
        search: "",
      },
    ],
    remotePatterns: [
      // new URL("https://lh3.googleusercontent.com/**"),
      // new URL("https://avatars.githubusercontent.com/**?v=*"),
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com/**",
        search: "",
      },
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com/**",
        search: "?v=4",
      },
    ],
  },
};

export default nextConfig;
