import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" } // Add password credential
      },
      async authorize(credentials) {
        // Check if username and password are provided
        if (!credentials?.username || !credentials?.password) {
          console.log("Missing username or password");
          return null;
        }
        
        try {
          // Call the new backend login endpoint
          const backendUrl = process.env.NEXT_PUBLIC_API_URL;
          if (!backendUrl) {
            throw new Error("Backend API URL not configured");
          }
          
          const res = await fetch(`${backendUrl}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          });
          
          const user = await res.json();

          // Check if login was successful on the backend
          if (res.ok && user.success) {
            console.log("Backend authentication successful for:", user.username);
            // Return user object for NextAuth session
            return {
              id: user.userId.toString(), // Ensure ID is a string
              name: user.username,
              // You can add other user properties here if needed
            };
          } else {
            // Log the error detail from the backend if available
            console.error("Backend authentication failed:", user.detail || res.statusText);
            // Throw an error that NextAuth can catch and display
            // Use a specific error code for invalid credentials
            if (res.status === 401) {
              throw new Error("InvalidCredentials");
            }
            throw new Error(user.detail || "Authentication failed");
          }
        } catch (error) {
          console.error("NextAuth authorize error:", error);
          // Rethrow the specific error for invalid credentials
          if (error instanceof Error && error.message === "InvalidCredentials") {
            throw error;
          }
          // Return null for other errors, or throw a generic error
          // Returning null is often preferred to avoid exposing internal details
          return null; 
        }
      },
    }),
  ],
  session: {
    strategy: "jwt", // Using JWT strategy is recommended
  },
  pages: {
    signIn: "/login",
    // You might want to add an error page:
    // error: '/auth/error', 
  },
  callbacks: {
    // Add callbacks if you need to customize session/token data
    async jwt({ token, user }) {
      // Persist the user ID onto the token
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      // Add user ID to the session object
      if (token && session.user) {
        session.user.id = token.id as string;
      }
      return session;
    },
  },
});

export { handler as GET, handler as POST };