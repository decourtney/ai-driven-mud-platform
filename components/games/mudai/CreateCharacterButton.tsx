"use client";

import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { CharacterState } from "@/app/types/game";

export default function CreateCharacterButton({
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
      const res = await fetch(`/api/play/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(playerState),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data = await res.json();
      localStorage.setItem(`${slug}Session`, JSON.stringify(data));

      router.push(`/play/${slug}/${data.session_id}`);
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
