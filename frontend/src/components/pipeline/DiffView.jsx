function lineClass(line) {
  if (line.startsWith("+++") || line.startsWith("---")) return "meta";
  if (line.startsWith("@@")) return "hunk";
  if (line.startsWith("+")) return "add";
  if (line.startsWith("-")) return "del";
  return "";
}

export default function DiffView({ patch }) {
  if (!patch) return null;

  return (
    <pre className="pl-diff">
      {patch.split("\n").map((line, index) => (
        <span key={index} className={`pl-diff-line ${lineClass(line)}`}>
          {line || " "}
        </span>
      ))}
    </pre>
  );
}
