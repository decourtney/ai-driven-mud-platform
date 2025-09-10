// app/play/[slug]/page.tsx
import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";
import GameBackground from "@/app/components/GameBackground";

export default async function GameMainMenu({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const gameComponents = getGameComponents(slug);

  if (!gameComponents) {
    notFound();
  }

  const MainMenu = await gameComponents.MainMenu();

  return (
    <GameBackground slug={slug}>
      <MainMenu.default slug={slug} />
    </GameBackground>
  );
}
