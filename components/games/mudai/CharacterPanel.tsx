import React, { ComponentType, useState } from "react";
import {
  User,
  Package,
  Scroll,
  Shield,
  Crown,
  Hand,
  Shirt,
} from "lucide-react";
import { CharacterPanelProps, EquipmentItem } from "@/app/types/game";

export default function CharacterPanel({
  character,
  equipped_gear: equippedGear,
  inventory,
  quests,
}: CharacterPanelProps) {
  const [activeTab, setActiveTab] = useState("gear");

  const EquipmentSlot = ({
    item,
    slotName,
    icon: Icon,
  }: {
    item?: EquipmentItem;
    slotName: string;
    icon: ComponentType<{ size: number; className?: string }>;
  }) => (
    <div className="bg-gray-800 border-2 border-gray-600 rounded-lg p-3 flex flex-col items-center justify-center h-20 hover:border-green-500 transition-colors cursor-pointer">
      <Icon size={20} className="text-gray-400 mb-1" />
      <div className="text-xs text-center">
        {item ? (
          <>
            <div className="text-green-400 font-mono text-xs truncate w-full">
              {item.name}
            </div>
            {item.defense && (
              <div className="text-gray-400">+{item.defense} DEF</div>
            )}
            {item.damage && (
              <div className="text-red-400">{item.damage} DMG</div>
            )}
          </>
        ) : (
          <div className="text-gray-500 capitalize">{slotName}</div>
        )}
      </div>
    </div>
  );

  const StatBar = ({
    current,
    max,
    color,
  }: {
    current: number;
    max: number;
    color: string;
  }) => (
    <div className="w-full bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300`}
        style={{
          width: `${(current / max) * 100}%`,
          backgroundColor: color,
        }}
      />
    </div>
  );

  const TabContent = () => {
    switch (activeTab) {
      case "gear":
        return (
          <div className="space-y-6">
            {/* Equipment Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div></div>
              <EquipmentSlot
                item={equippedGear?.helm}
                slotName="helm"
                icon={Crown}
              />
              <div></div>

              <EquipmentSlot
                item={equippedGear?.weapon}
                slotName="weapon"
                icon={Shield}
              />
              <EquipmentSlot
                item={equippedGear?.armor}
                slotName="armor"
                icon={Shirt}
              />
              <EquipmentSlot
                item={equippedGear?.shield}
                slotName="shield"
                icon={Shield}
              />

              <EquipmentSlot
                item={equippedGear?.hands}
                slotName="hands"
                icon={Hand}
              />
              <EquipmentSlot
                item={equippedGear?.legs}
                slotName="legs"
                icon={Shirt}
              />
              <div></div>
            </div>

            {/* Character Stats */}
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-600">
              <h3 className="text-green-400 font-mono font-bold mb-3 text-center">
                CHARACTER STATS
              </h3>

              {/* Health and Mana */}
              <div className="space-y-2 mb-4">
                <div>
                  <div className="flex justify-between text-sm font-mono">
                    <span className="text-red-400">HP</span>
                    <span className="text-white">
                      {character?.hp}/{character?.max_hp}
                    </span>
                  </div>
                  <StatBar
                    current={character?.hp || 0}
                    max={character?.max_hp || 1}
                    color="#ef4444"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm font-mono">
                    <span className="text-blue-400">MP</span>
                    <span className="text-white">
                      {character?.mp}/{character?.max_mp}
                    </span>
                  </div>
                  <StatBar
                    current={character?.mp || 0}
                    max={character?.max_mp || 1}
                    color="#3b82f6"
                  />
                </div>
              </div>

              {/* Core Stats */}
              <div className="grid grid-cols-2 gap-2 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-gray-300">STR</span>
                  <span className="text-white">
                    {character?.stats?.strength || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">DEX</span>
                  <span className="text-white">
                    {character?.stats?.dexterity || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">CON</span>
                  <span className="text-white">
                    {character?.stats?.constitution || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">INT</span>
                  <span className="text-white">
                    {character?.stats?.intelligence || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">WIS</span>
                  <span className="text-white">
                    {character?.stats?.wisdom || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">CHA</span>
                  <span className="text-white">
                    {character?.stats?.charisma || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case "inventory":
        return (
          <div className="space-y-2">
            <h3 className="text-green-400 font-mono font-bold text-center mb-4">
              INVENTORY
            </h3>
            {inventory?.map((item) => (
              <div
                key={item.id}
                className="bg-gray-800 border border-gray-600 rounded p-3 hover:bg-gray-700 transition-colors cursor-pointer"
              >
                <div className="flex justify-between items-center">
                  <span className="text-white font-mono">{item.name}</span>
                  <span className="text-green-400 font-mono">
                    x{item.quantity}
                  </span>
                </div>
                <div className="text-xs text-gray-400 capitalize">
                  {item.type}
                </div>
              </div>
            ))}
            {(!inventory || inventory.length === 0) && (
              <div className="text-center text-gray-500 font-mono">
                No items in inventory
              </div>
            )}
          </div>
        );

      case "quests":
        return (
          <div className="space-y-2">
            <h3 className="text-green-400 font-mono font-bold text-center mb-4">
              QUESTS
            </h3>
            {quests?.map((quest) => (
              <div
                key={quest.id}
                className="bg-gray-800 border border-gray-600 rounded p-3 hover:bg-gray-700 transition-colors cursor-pointer"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-white font-mono text-sm">
                    {quest.name}
                  </span>
                  <span
                    className={`text-xs font-mono px-2 py-1 rounded ${
                      quest.status === "completed"
                        ? "bg-green-600 text-white"
                        : "bg-yellow-600 text-white"
                    }`}
                  >
                    {quest.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  Progress: {quest.progress}
                </div>
              </div>
            ))}
            {(!quests || quests.length === 0) && (
              <div className="text-center text-gray-500 font-mono">
                No active quests
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col w-full bg-gray-900 border-r border-green-500">
      {/* Character Header */}
      <div className="bg-gray-800 border-b border-green-500 p-4">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center">
            <User size={24} className="text-black" />
          </div>
          <div>
            <h2 className="text-green-400 font-mono font-bold text-lg">
              {character?.name || "Loading..."}
            </h2>
            <p className="text-gray-300 font-mono text-sm">
              Level {character?.level || 0} {character?.class || "Unknown"}
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-green-500">
        <button
          onClick={() => setActiveTab("gear")}
          className={`flex-1 p-3 font-mono text-sm transition-colors ${
            activeTab === "gear"
              ? "bg-green-600 text-black"
              : "text-green-400 hover:bg-gray-800"
          }`}
        >
          <Shield size={16} className="mx-auto mb-1" />
          GEAR
        </button>
        <button
          onClick={() => setActiveTab("inventory")}
          className={`flex-1 p-3 font-mono text-sm transition-colors ${
            activeTab === "inventory"
              ? "bg-green-600 text-black"
              : "text-green-400 hover:bg-gray-800"
          }`}
        >
          <Package size={16} className="mx-auto mb-1" />
          ITEMS
        </button>
        <button
          onClick={() => setActiveTab("quests")}
          className={`flex-1 p-3 font-mono text-sm transition-colors ${
            activeTab === "quests"
              ? "bg-green-600 text-black"
              : "text-green-400 hover:bg-gray-800"
          }`}
        >
          <Scroll size={16} className="mx-auto mb-1" />
          QUESTS
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        <TabContent />
      </div>
    </div>
  );
}
