export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="text-gray-500 text-sm mt-2">Coming in Phase 5.</p>
    </div>
  );
}
