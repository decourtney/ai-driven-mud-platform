import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";

export default async function GamePage({
  params,
}: {
  params: { slug: string; id: string };
}) {
  const gameComponents = getGameComponents(params.slug);

  if (!gameComponents) {
    notFound();
  }

  const GamePage = await gameComponents.GamePage();
  return <GamePage.default slug={params.slug} id={params.id} />;
}
