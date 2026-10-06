import type { AgentName } from "./types";

export interface AgentPersona {
  name: string;
  role: string;
  initials: string;
  accent: string; // CSS color used for this agent's nameplate/border
}

export const AGENTS: Record<AgentName, AgentPersona> = {
  boss: { name: "Handsome Dan", role: "Boss", initials: "HD", accent: "#1e3a6e" },
  inventory: { name: "Sterling", role: "Inventory", initials: "ST", accent: "#5b3a29" },
  accounting: { name: "Ledger", role: "Accounting", initials: "LG", accent: "#2f5538" },
  facilities: { name: "Harkness", role: "Facilities", initials: "HK", accent: "#6b6358" },
  customer_service: { name: "Clark", role: "Customer Service", initials: "CL", accent: "#8a2e2e" },
};

export function personaFor(agentKey: string): AgentPersona {
  return (
    AGENTS[agentKey as AgentName] ?? {
      name: agentKey,
      role: "Agent",
      initials: agentKey.slice(0, 2).toUpperCase(),
      accent: "#6b6358",
    }
  );
}
