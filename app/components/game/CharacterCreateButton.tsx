"use client";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { CharacterState } from "../../types/game";

export default function CharacterCreateButton({
  playerState,
  slug,
  availablePoints,
}: {
  playerState: CharacterState;
  slug: string;
  availablePoints: number;
}) {
  const router = useRouter();

  const handleSubmit = async () => {
    try {
      const res = await fetch(`/api/sessions/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(playerState),
      });

      const data = await res.json();

      if (!res.ok) {
        toast.error(data.error || "Failed to create character");
        return;
      }

      router.push(`/games/${slug}/play/${data.session_id}`);
    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
    }
  };

  return (
    <button
      onClick={handleSubmit}
      disabled={!playerState.name.trim() || availablePoints > 0}
      className="w-full mt-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-bold py-3 transition-colors"
    >
      CREATE CHARACTER
    </button>
  );
}
