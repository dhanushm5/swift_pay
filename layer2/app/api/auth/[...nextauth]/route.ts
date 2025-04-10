import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
      },
      async authorize(credentials) {
        if (!credentials?.username) return null;
        
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: credentials.username }),
          });
          
          const user = await res.json();
          
          if (user.exists) {
            return {
              id: user.userId,
              name: credentials.username,
            };
          }
          
          // If user doesn't exist, create one
          const createRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: credentials.username }),
          });
          
          const newUser = await createRes.json();
          
          if (newUser.success) {
            return {
              id: newUser.userId,
              name: credentials.username,
            };
          }
          
          return null;
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
});

export { handler as GET, handler as POST };