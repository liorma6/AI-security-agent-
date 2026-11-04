import { readFileSync } from 'node:fs';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

export const schema = JSON.parse(readFileSync(new URL('../schemas/contracts.schema.json', import.meta.url), 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
ajv.addSchema(schema);
const validators = new Map(Object.keys(schema.$defs).map((name) => [
  name, ajv.getSchema(schema.$id + '#/$defs/' + name),
]));

export function validateContract(name, value) {
  const validate = validators.get(name);
  if (!validate) throw new Error('Unknown contract: ' + name);
  const valid = validate(value);
  return { valid, errors: valid ? [] : structuredClone(validate.errors) };
}
