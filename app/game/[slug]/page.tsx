import { notFound } from "next/navigation";
import axios from "axios";

export default async function GamePage({
  params,
}: {
  params: { slug: string };
}) {
  const res = await axios
    .get(`${process.env.NEXT_PUBLIC_BASE_URL}/games/${params.slug}`)
    .catch(() => notFound());

  const game = res.data;

  return (
    <div>
      <h1>{game.title}</h1>
      <p>{game.description}</p>
    </div>
  );
}
