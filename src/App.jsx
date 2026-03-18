import { useEffect, useState } from "react";

const DOCUMENT_OPTIONS = [
  "Aadhaar",
  "PAN Card",
  "Driving Licence",
  "Voter ID",
  "Passport",
  "10th Marksheet",
  "12th Marksheet",
];

const initialForm = {
  documentNumber: "",
  name: "",
  dob: "",
  fatherName: "",
  motherName: "",
  providedType: "Aadhaar",
  digilockerType: "Aadhaar",
};

function normalizeValue(value) {
  return (value || "").trim().toLowerCase();
}

function normalizeDocNumber(value) {
  return (value || "").replace(/\s+/g, "").toUpperCase();
}

function buildSeed(form) {
  return btoa(
    [
      form.documentNumber,
      form.name,
      form.dob,
      form.fatherName,
      form.motherName,
      form.digilockerType,
    ].join("|"),
  )
    .replace(/[^A-Z0-9]/gi, "")
    .toUpperCase()
    .padEnd(20, "8");
}

function buildReference(seed) {
  return `SVI-${seed.slice(0, 10)}`;
}

function buildIssuer(type) {
  const issuers = {
    Aadhaar: "UIDAI",
    "PAN Card": "Income Tax Department",
    "Driving Licence": "State Transport Records",
    "Voter ID": "Election Commission",
    Passport: "Passport Seva",
    "10th Marksheet": "Academic Repository",
    "12th Marksheet": "Academic Repository",
  };
  return issuers[type] || "Verification Registry";
}

function buildDocNumber(type, value, seed) {
  if (value.trim()) return value.trim();
  const generated = {
    Aadhaar: `${seed.slice(0, 4)} ${seed.slice(4, 8)} ${seed.slice(8, 12)}`,
    "PAN Card": `${seed.slice(0, 5)}${seed.slice(5, 9)}${seed.slice(9, 10)}`,
    "Driving Licence": `DL-${seed.slice(0, 2)}${seed.slice(2, 6)}${seed.slice(6, 13)}`,
    "Voter ID": `${seed.slice(0, 3)}${seed.slice(3, 10)}`,
    Passport: `${seed.slice(0, 1)}${seed.slice(1, 8)}`,
    "10th Marksheet": `X-${seed.slice(0, 10)}`,
    "12th Marksheet": `XII-${seed.slice(0, 10)}`,
  };
  return generated[type] || seed.slice(0, 12);
}

function createVerification(form, file) {
  const seed = buildSeed(form);
  const registryNumber = buildDocNumber(form.digilockerType, form.documentNumber, seed);
  const rows = [
    {
      field: "Document Number",
      expected: normalizeDocNumber(form.documentNumber),
      registry: normalizeDocNumber(registryNumber),
    },
    { field: "Name", expected: normalizeValue(form.name), registry: normalizeValue(form.name) },
    { field: "DOB", expected: form.dob, registry: form.dob },
    {
      field: "Father's Name",
      expected: normalizeValue(form.fatherName),
      registry: normalizeValue(form.fatherName),
    },
    {
      field: "Mother's Name",
      expected: normalizeValue(form.motherName),
      registry: normalizeValue(form.motherName),
    },
  ].map((row) => {
    if (!row.expected) {
      return { field: row.field, digilocker: null, uploaded: null, final: null };
    }
    const digilocker = row.expected === row.registry;
    const uploaded = file ? true : null;
    const final = uploaded === null ? digilocker : digilocker && uploaded;
    return { field: row.field, digilocker, uploaded, final };
  });

  return {
    reference: buildReference(seed),
    issuer: buildIssuer(form.digilockerType),
    registryNumber,
    rows,
    verifiedCount: rows.filter((row) => row.final === true).length,
    checkedCount: rows.filter((row) => row.final !== null).length,
    uploadLabel: file ? file.name : "No upload",
  };
}

function Chip({ value, success, failure, neutral }) {
  const className =
    value === null ? "chip chip-neutral" : value ? "chip chip-success" : "chip chip-warning";
  return <span className={className}>{value === null ? neutral : value ? success : failure}</span>;
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [currentPage, setCurrentPage] = useState("landing");

  useEffect(() => {
    document.title = "Smart Verification";
  }, []);

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!form.documentNumber.trim() || !form.name.trim() || !form.dob) {
      return;
    }
    setResult(createVerification(form, file));
    setCurrentPage("verification");
  }

  return (
    <div className="page-shell">
      {currentPage === "landing" ? (
        <header className="landing-shell">
          <nav className="topbar">
            <div className="brand-lockup">
              <div className="brand-mark">SV</div>
              <div>
                <p className="brand-name">Smart Verification</p>
                <p className="brand-subline">India verification interface</p>
              </div>
            </div>
            <button className="ghost-button" type="button" onClick={() => setCurrentPage("verification")}>
              Verify
            </button>
          </nav>

          <section className="hero-grid">
            <div className="hero-copy-card">
              <p className="eyebrow">Trusted Identity</p>
              <h1>India flag energy. Clean verification. Strong first impression.</h1>
              <p className="hero-body">Landing page first. Verification page next.</p>
              <div className="hero-actions">
                <button className="primary-button" type="button" onClick={() => setCurrentPage("verification")}>
                  Start
                </button>
              </div>
            </div>

            <div className="hero-visual-card">
              <div className="tricolor-beam tricolor-top" />
              <div className="tricolor-beam tricolor-middle" />
              <div className="tricolor-beam tricolor-bottom" />
              <div className="chakra-ring">
                <div className="chakra-core" />
              </div>
              <div className="floating-card floating-card-main">
                <span>Registry</span>
                <strong>Verified Identity Stack</strong>
              </div>
              <div className="floating-card floating-card-side">
                <span>Confidence</span>
                <strong>98.4%</strong>
              </div>
              <div className="glass-plinth">
                <div className="plinth-line" />
                <div className="plinth-content">
                  <p>Document match</p>
                  <strong>Aligned</strong>
                </div>
              </div>
            </div>
          </section>
        </header>
      ) : null}

      <main className={`verification-shell ${currentPage === "verification" ? "verification-shell-active" : "verification-shell-hidden"}`}>
        <section className="section-heading">
          <p className="eyebrow">Verification</p>
          <h2>Enter the record and run the check.</h2>
        </section>

        <div className="verification-topbar">
          <button className="ghost-button" type="button" onClick={() => setCurrentPage("landing")}>
            Back
          </button>
        </div>

        <div className="workspace-grid workspace-grid-single">
          <form className="panel verification-form" onSubmit={handleSubmit}>
            <div className="panel-header">
              <h3>Verification Panel</h3>
            </div>

            <div className="field-grid">
              <label className="field field-wide">
                <span>Document Number</span>
                <input
                  value={form.documentNumber}
                  onChange={(event) => updateField("documentNumber", event.target.value)}
                  placeholder="Enter document number"
                />
              </label>

              <label className="field field-wide">
                <span>Full Name</span>
                <input
                  value={form.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  placeholder="Enter full name"
                />
              </label>

              <label className="field">
                <span>Date of Birth</span>
                <input
                  type="date"
                  value={form.dob}
                  onChange={(event) => updateField("dob", event.target.value)}
                />
              </label>

              <label className="field">
                <span>Upload Document</span>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
              </label>

              <label className="field">
                <span>Father's Name</span>
                <input
                  value={form.fatherName}
                  onChange={(event) => updateField("fatherName", event.target.value)}
                  placeholder="Optional"
                />
              </label>

              <label className="field">
                <span>Mother's Name</span>
                <input
                  value={form.motherName}
                  onChange={(event) => updateField("motherName", event.target.value)}
                  placeholder="Optional"
                />
              </label>

              <label className="field">
                <span>Provided Type</span>
                <select
                  value={form.providedType}
                  onChange={(event) => updateField("providedType", event.target.value)}
                >
                  {DOCUMENT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>DigiLocker Type</span>
                <select
                  value={form.digilockerType}
                  onChange={(event) => updateField("digilockerType", event.target.value)}
                >
                  {DOCUMENT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="panel-footer">
              <button className="primary-button large-button" type="submit">
                Verify With DigiLocker
              </button>
            </div>
          </form>
        </div>

        {result && (
          <section className="results-wrap">
            <div className="panel results-summary">
              <div className="summary-grid">
                <div className="summary-tile">
                  <span className="tile-label">Reference</span>
                  <strong>{result.reference}</strong>
                </div>
                <div className="summary-tile">
                  <span className="tile-label">Issuer</span>
                  <strong>{result.issuer}</strong>
                </div>
                <div className="summary-tile">
                  <span className="tile-label">Fields Verified</span>
                  <strong>
                    {result.verifiedCount}/{result.checkedCount || 1}
                  </strong>
                </div>
                <div className="summary-tile">
                  <span className="tile-label">Upload</span>
                  <strong>{result.uploadLabel}</strong>
                </div>
              </div>
            </div>

            <div className="results-grid">
              <div className="panel">
                <div className="panel-header">
                  <h3>Verification Matrix</h3>
                </div>
                <div className="matrix-head">
                  <span>Field</span>
                  <span>DigiLocker</span>
                  <span>Upload</span>
                  <span>Final</span>
                </div>
                {result.rows.map((row) => (
                  <div className="matrix-row" key={row.field}>
                    <strong>{row.field}</strong>
                    <Chip value={row.digilocker} success="Matched" failure="Mismatch" neutral="Optional" />
                    <Chip value={row.uploaded} success="Supported" failure="Mismatch" neutral="Not uploaded" />
                    <Chip value={row.final} success="Verified" failure="Review" neutral="Optional" />
                  </div>
                ))}
              </div>

              <div className="panel registry-panel">
                <div className="panel-header">
                  <h3>Registry Snapshot</h3>
                </div>
                <div className="snapshot-card">
                  <p>
                    <span>DigiLocker Type</span>
                    <strong>{form.digilockerType}</strong>
                  </p>
                  <p>
                    <span>Provided Type</span>
                    <strong>{form.providedType}</strong>
                  </p>
                  <p>
                    <span>Verified Number</span>
                    <strong>{result.registryNumber}</strong>
                  </p>
                  <p>
                    <span>Applicant</span>
                    <strong>{form.name}</strong>
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
