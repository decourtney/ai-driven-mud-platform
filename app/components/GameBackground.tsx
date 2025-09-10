interface GameBackgroundProps {
  slug: string;
  children: React.ReactNode;
}

export default function GameBackground({
  slug,
  children,
}: GameBackgroundProps) {
  return (
    <>
      {/* Background Image */}
      <div className="absolute inset-0 w-full h-full -z-20">
        <img
          src={`/images/${slug}.jpeg`}
          alt={`${slug} adventure scene`}
          className="w-full h-full object-cover"
          style={{
            filter: "contrast(1.1) brightness(0.5) sepia(0.5) saturate(0.7)",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/20 to-transparent"></div>
      </div>
      {children}
    </>
  );
}
