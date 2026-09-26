// Field bounds for the Submit form, read from the committed OpenAPI schema so the client-side
// mirror of BR-VAL-001/002 is the server's rule, not a second copy of it (FR-FE-002, FR-FE-018).
import schema from "./openapi.json";

interface Bounds {
  min: number;
  max: number;
}

const create = schema.components.schemas.ComplaintCreate.properties;
const contactMax = create.reporter_contact.anyOf.find((option) => "maxLength" in option);

export const TEXT: Bounds = { min: create.text.minLength, max: create.text.maxLength };
export const LOCATION: Bounds = { min: create.location.minLength, max: create.location.maxLength };
export const CONTACT_MAX: number =
  contactMax && "maxLength" in contactMax ? (contactMax.maxLength as number) : Infinity;
