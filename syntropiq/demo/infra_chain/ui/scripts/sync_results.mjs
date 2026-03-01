import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const source = path.resolve(__dirname, "../../outputs/infra_chain_results.json");
const targetDir = path.resolve(__dirname, "../public");
const target = path.resolve(targetDir, "infra_chain_results.json");

fs.mkdirSync(targetDir, { recursive: true });

if (!fs.existsSync(source)) {
  const fallback = {
    summary: {},
    timeline: []
  };
  fs.writeFileSync(target, JSON.stringify(fallback, null, 2));
  console.log(`Source not found at ${source}. Wrote fallback to ${target}`);
  process.exit(0);
}

fs.copyFileSync(source, target);
console.log(`Copied ${source} -> ${target}`);
