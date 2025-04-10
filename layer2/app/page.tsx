import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { Dashboard } from "@/components/dashboard";

// Force dynamic rendering for this page
export const dynamic = 'force-dynamic';

export default async function Home() {
  const session = await getServerSession();
  
  if (!session) {
    redirect("/login");
  }

  return <Dashboard />;
}