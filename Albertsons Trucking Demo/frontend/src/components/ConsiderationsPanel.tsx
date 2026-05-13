export default function ConsiderationsPanel({ items, relaxed }: { items: string[]; relaxed: string[] }) {
  return (
    <div className="considerations">
      <h4>Considerations applied</h4>
      <ul>{items.map((c, i) => <li key={i}>{c}</li>)}</ul>
      {relaxed.length > 0 && (
        <>
          <h4>Constraints relaxed</h4>
          <ul className="relaxed">{relaxed.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </>
      )}
    </div>
  );
}
