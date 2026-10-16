// Art direction only. Names, captions, products and availability remain catalog data.
const departments = {
  all: {
    title: "SMALL MACHINES.\nBIG IDEAS.",
    label: "The product directory",
    note: "Software with personality. Hardware with possibility. A few good things for your corner of the future.",
    motif: "directory",
  },
  apps: {
    title: "YOUR MACHINE.\nMORE POSSIBILITIES.",
    label: "The software library",
    note: "Make room for a different kind of desktop. Explore the RODDY software shelf.",
    motif: "software",
  },
  games: {
    title: "PRESS START.\nGO SOMEWHERE.",
    label: "The games department",
    note: "A little escape. A strange new world. Find your next reason to stay for one more round.",
    motif: "arcade",
  },
  video: {
    title: "PRESS PLAY.\nKEEP THE PICTURE.",
    label: "The video library",
    note: "Vintage tapes. Classic films. Movies for unexpected machines. Welcome to RODDY VIDEO.",
    motif: "video",
  },
  computers: {
    title: "A DIFFERENT\nKIND OF PERSONAL.",
    label: "The computing division",
    note: "The computer as an invitation. Explore what is taking shape on the RODDY workbench.",
    motif: "engineering",
  },
  labs: {
    title: "WHAT IF?\nLET’S FIND OUT.",
    label: "The experimental division",
    note: "The place for curious machines, unfinished questions, and ideas worth trying.",
    motif: "engineering",
  },
  kits: {
    title: "YOUR WORKBENCH.\nYOUR NEXT PROJECT.",
    label: "The kits department",
    note: "Board kits, completion parts and free case files for building your own RODDY hardware. Check each listing for prototype status and availability.",
    motif: "engineering",
  },
  merch: {
    title: "OFF THE SCREEN.\nINTO YOUR WORLD.",
    label: "The company store",
    note: "For your desk. For your everyday. A little RODDY, wherever you make things happen.",
    motif: "merch",
  },
};

export function departmentDirection(id) {
  return (
    departments[id] || {
      ...departments.all,
      title: "SOMETHING ELSE.\nSOMETHING RODDY.",
    }
  );
}
