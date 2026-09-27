import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, type Complaint, createComplaint } from "../api/client";
import { CONTACT_MAX, LOCATION, TEXT } from "../api/limits";
import ErrorBanner from "../components/ErrorBanner";
import TriageResult from "../components/TriageResult";

type Field = "text" | "location" | "reporter_contact";
type Values = Record<Field, string>;
type FieldErrors = Partial<Record<Field, string>>;

const EMPTY: Values = { text: "", location: "", reporter_contact: "" };

/** Mirrors the server's bounds for a fast inline hint; the server stays the authority
 *  (BR-VAL-001/002). Lengths are measured after trimming, exactly as the API does. */
function validate(values: Values): FieldErrors {
  const errors: FieldErrors = {};
  const text = values.text.trim().length;
  const location = values.location.trim().length;
  if (text < TEXT.min || text > TEXT.max) {
    errors.text = `Complaint must be ${TEXT.min}–${TEXT.max} characters (currently ${text}).`;
  }
  if (location < LOCATION.min || location > LOCATION.max) {
    errors.location = `Location must be ${LOCATION.min}–${LOCATION.max} characters (currently ${location}).`;
  }
  if (values.reporter_contact.trim().length > CONTACT_MAX) {
    errors.reporter_contact = `Contact must be at most ${CONTACT_MAX} characters.`;
  }
  return errors;
}

function isField(name: string): name is Field {
  return name === "text" || name === "location" || name === "reporter_contact";
}

export default function SubmitPage() {
  const [values, setValues] = useState<Values>(EMPTY);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);
  const [rateLimit, setRateLimit] = useState<ApiError | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => () => inFlight.current?.abort(), []); // abort on unmount (FR-FE-003)

  const update = (field: Field) => (value: string) => setValues((v) => ({ ...v, [field]: value }));
  const blur = (field: Field) => () =>
    setFieldErrors((current) => ({ ...current, [field]: validate(values)[field] }));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    const errors = validate(values);
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) return; // blocked: no request is issued

    setSubmitting(true);
    setResult(null);
    setRateLimit(null);
    setFailure(null);
    const controller = new AbortController();
    inFlight.current = controller;
    try {
      const contact = values.reporter_contact.trim();
      const complaint = await createComplaint(
        {
          text: values.text,
          location: values.location,
          ...(contact ? { reporter_contact: contact } : {}),
        },
        controller.signal,
      );
      setResult(complaint);
      setValues(EMPTY);
    } catch (error) {
      if (controller.signal.aborted) return;
      if (!(error instanceof ApiError)) throw error;
      if (error.status === 400 && error.fields.length > 0) {
        // Map the server's field errors back onto the inputs that caused them.
        const mapped: FieldErrors = {};
        for (const f of error.fields) if (isField(f.field)) mapped[f.field] = f.detail;
        if (Object.keys(mapped).length > 0) setFieldErrors(mapped);
        else setFailure(error);
      } else if (error.status === 429) {
        setRateLimit(error);
      } else {
        setFailure(error);
      }
    } finally {
      if (!controller.signal.aborted) setSubmitting(false);
    }
  }

  return (
    <section>
      <h2>Report a problem</h2>
      <form onSubmit={onSubmit} noValidate className="form">
        <FieldInput
          id="text"
          label="What is the problem?"
          multiline
          value={values.text}
          error={fieldErrors.text}
          onChange={update("text")}
          onBlur={blur("text")}
        />
        <FieldInput
          id="location"
          label="Where is it?"
          value={values.location}
          error={fieldErrors.location}
          onChange={update("location")}
          onBlur={blur("location")}
        />
        <FieldInput
          id="reporter_contact"
          label="Contact (optional)"
          value={values.reporter_contact}
          error={fieldErrors.reporter_contact}
          onChange={update("reporter_contact")}
          onBlur={blur("reporter_contact")}
        />
        <button type="submit" disabled={submitting} data-testid="submit">
          {submitting ? "Submitting…" : "Submit report"}
        </button>
        {submitting && (
          <p role="status" className="progress" data-testid="loading">
            <span className="spinner" aria-hidden="true" /> Classifying your report… this can take up
            to half a minute.
          </p>
        )}
      </form>

      {rateLimit && (
        <div role="alert" className="banner warning" data-testid="error-ratelimit">
          <p>You are submitting too quickly.</p>
          <p>
            Please wait {rateLimit.retryAfterSeconds ?? "a few"} seconds before trying again.
          </p>
          <p className="request-id">
            Request ID: <code>{rateLimit.requestId}</code>
          </p>
        </div>
      )}
      {failure && <ErrorBanner error={failure} />}
      {result && <TriageResult complaint={result} />}
    </section>
  );
}

interface FieldInputProps {
  id: Field;
  label: string;
  value: string;
  error: string | undefined;
  multiline?: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
}

function FieldInput({ id, label, value, error, multiline, onChange, onBlur }: FieldInputProps) {
  const errorId = `${id}-error`;
  const common = {
    id,
    name: id,
    value,
    onBlur,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? errorId : undefined,
  };
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea {...common} rows={5} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input {...common} type="text" onChange={(e) => onChange(e.target.value)} />
      )}
      {error && (
        <p id={errorId} className="field-error" data-testid="error-field" data-field={id}>
          {error}
        </p>
      )}
    </div>
  );
}
