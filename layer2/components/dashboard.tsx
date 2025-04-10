"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { TransactionList } from "@/components/transaction-list";
import { SendMoneyDialog } from "@/components/send-money-dialog";
import { AddBalanceDialog } from "@/components/add-balance-dialog";
import { UserNav } from "@/components/user-nav";
import { Loader2 } from "lucide-react";

export function Dashboard() {
  const { data: session } = useSession();
  const [balance, setBalance] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  const fetchBalance = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/balance/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: session?.user?.name }),
      });
      
      const data = await res.json();
      setBalance(data.balance);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch balance",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (session?.user?.name) {
      fetchBalance();
    }
  }, [session]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b">
        <div className="flex h-16 items-center px-4">
          <div className="ml-auto flex items-center space-x-4">
            <UserNav />
          </div>
        </div>
      </div>
      
      <div className="container mx-auto py-10">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="p-6">
            <h3 className="text-lg font-medium">Balance</h3>
            <p className="mt-2 text-3xl font-bold">{balance}</p>
          </Card>
        </div>

        <div className="mt-8 flex space-x-4">
          <SendMoneyDialog onSuccess={fetchBalance} />
          <AddBalanceDialog onSuccess={fetchBalance} />
        </div>

        <div className="mt-8">
          <TransactionList />
        </div>
      </div>
    </div>
  );
}