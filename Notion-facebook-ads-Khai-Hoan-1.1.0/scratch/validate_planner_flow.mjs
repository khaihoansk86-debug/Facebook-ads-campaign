import fs from "node:fs";

const catalog = JSON.parse(fs.readFileSync("config/planner_bundles.json", "utf8"));
const mappingSource = fs.readFileSync("ads_core/mapping.py", "utf8");

function aliasKeys(section) {
  const marker = `    "${section}": {`;
  const start = mappingSource.indexOf(marker);
  if (start < 0) return [];
  const rest = mappingSource.slice(start + marker.length);
  const end = rest.indexOf("\n    },");
  const block = end >= 0 ? rest.slice(0, end) : rest;
  return [...block.matchAll(/"([^"]+)"\s*:/g)].map((match) => match[1]);
}

function value(values, primary, legacy) {
  return values[primary] || values[legacy] || "";
}

const goalAliases = new Set(aliasKeys("Mục tiêu tối ưu"));
const destinationAliases = new Set(aliasKeys("Vị trí chuyển đổi"));

const missingGoals = [];
const missingDestinations = [];
for (const bundle of catalog.adSetBundles || []) {
  const values = bundle.notionValues || {};
  const goal = value(values, "Mục tiêu tối ưu", "Má»¥c tiÃªu tá»‘i Æ°u");
  const destination = value(values, "Vị trí chuyển đổi", "Vá»‹ trÃ­ chuyá»ƒn Ä‘á»•i");
  if (goal && !goalAliases.has(goal)) missingGoals.push(`${bundle.code}: ${goal}`);
  if (destination && !destinationAliases.has(destination)) {
    missingDestinations.push(`${bundle.code}: ${destination}`);
  }
}

const missingCampaignObjectives = (catalog.campaignBundles || [])
  .filter((bundle) => !value(bundle.notionValues || {}, "Mục tiêu chiến dịch", "Má»¥c tiÃªu chiáº¿n dá»‹ch"))
  .map((bundle) => bundle.code);

console.log(`campaigns=${catalog.campaignBundles.length}`);
console.log(`adsets=${catalog.adSetBundles.length}`);
console.log(`missingGoals=${missingGoals.length}`);
if (missingGoals.length) console.log(missingGoals.join("\n"));
console.log(`missingDestinations=${missingDestinations.length}`);
if (missingDestinations.length) console.log(missingDestinations.join("\n"));
console.log(`missingCampaignObjectives=${missingCampaignObjectives.length}`);
if (missingCampaignObjectives.length) console.log(missingCampaignObjectives.join("\n"));
console.log(
  "awarenessGoals=" +
    catalog.adSetBundles
      .filter((bundle) => bundle.campaignBundleCode === "AWARENESS_BASE")
      .map((bundle) => bundle.performanceGoal)
      .join(" | "),
);
console.log(`badMarkers=${/Ãƒ|Ã†|Ã¡Â»|Ã„/.test(JSON.stringify(catalog)) || /Ãƒ|Ã†|Ã¡Â»|Ã„/.test(mappingSource)}`);
