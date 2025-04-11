import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { RegisterForm } from "@/components/register-form"; // We will create this next

export default async function RegisterPage() {
  const session = await getServerSession();

  // If user is already logged in, redirect to home
  if (session) {
    redirect("/");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white shadow-md rounded-lg">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Create your SwiftPay Account
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Enter a username and password to register
          </p>
        </div>
        <RegisterForm />
      </div>
    </div>
  );
}
