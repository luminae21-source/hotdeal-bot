import { ROOT, readCards, cardStatus, assertValid, parseArgs, isMain } from './common.mjs';

export async function validateFiles({ root = ROOT, data } = {}) {
  const cards = await readCards(root, data);
  for (const card of cards) {
    console.log(`${cardStatus(card).toUpperCase()} ${card.file}`);
    for (const warning of card.result.warnings ?? []) console.warn(`  warning: ${typeof warning === 'string' ? warning : `${warning.path ?? ''} ${warning.message ?? JSON.stringify(warning)}`}`);
  }
  assertValid(cards);
  console.log(`Validated ${cards.length} file(s); blank drafts do not create cards.`);
  return cards;
}
if (isMain(import.meta.url)) {
  try { await validateFiles(parseArgs(process.argv.slice(2))); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
