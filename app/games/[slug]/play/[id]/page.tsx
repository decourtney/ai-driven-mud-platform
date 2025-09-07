// app/games/[slug]/play/[id]/page.tsx
import GameBackground from "@/components/GameBackground";
import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";

export default async function GamePage({
  params,
}: {
  params: Promise<{ slug: string; id: string }>;
}) {
  const { slug, id } = await params;
  const gameComponents = getGameComponents(slug);

  if (!gameComponents) {
    notFound();
  }

  const GamePage = await gameComponents.GamePage();
  return (
    <GameBackground slug={slug}>
      <GamePage.default slug={slug} id={id} />
    </GameBackground>
  );
}
