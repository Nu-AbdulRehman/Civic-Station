import { useEffect, useState } from "react";
import { getVersion, type VersionInfo } from "../api/client";
import { PROVIDER_LABEL } from "../api/labels";

/**
 * Which build and which classifier are serving this page, from GET /api/version (FR-BE-029).
 * A failed call only drops the version line; the footer never breaks the page.
 */
export default function SiteFooter() {
  const [info, setInfo] = useState<VersionInfo | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getVersion(controller.signal)
      .then(setInfo)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  return (
    <footer className="site-footer" data-testid="site-footer">
      Civic-Station
      {info && (
        <>
          {" · version "}
          <code title={info.version}>{info.version.slice(0, 7)}</code>
          {" · classifier: "}
          {PROVIDER_LABEL[info.provider]}
        </>
      )}
    </footer>
  );
}
