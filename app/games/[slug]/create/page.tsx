import { getGameComponents } from "@/lib/games/registry";
import { notFound } from "next/navigation";

export default async function CreateCharacter({
  params,
}: {
  params: { slug: string };
}) {
  const gameComponents = getGameComponents(params.slug);

  if (!gameComponents) {
    notFound();
  }

  const CreateCharacter = await gameComponents.CreateCharacter();
  return <CreateCharacter.default slug={params.slug} />;
}
