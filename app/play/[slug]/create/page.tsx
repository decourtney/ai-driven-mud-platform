// app/play/[slug]/create/page.tsx
import GameBackground from "@/app/components/GameBackground";
import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";

export default async function CreateCharacter({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const gameComponents = getGameComponents(slug);

  if (!gameComponents) {
    notFound();
  }

  const CreateCharacter = await gameComponents.CreateCharacter();
  return (
    <GameBackground slug={slug}>
      <CreateCharacter.default slug={slug} />
    </GameBackground>
  );
}
