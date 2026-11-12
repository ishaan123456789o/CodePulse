import Link from "next/link";
export default function NotFound() {
  return (
    <div className="state-box">
      <h1>Page not found</h1>
      <p>This page is not in the CodePulse index.</p>
      <Link href="/">Return to overview</Link>
    </div>
  );
}
