import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";

export default async function GameMainMenu({
  params,
}: {
  params: { slug: string };
}) {
  const gameComponents = getGameComponents(params.slug);

  if (!gameComponents) {
    notFound();
  }

  const MainMenu = await gameComponents.MainMenu();
  return <MainMenu.default slug={params.slug} />;
}
