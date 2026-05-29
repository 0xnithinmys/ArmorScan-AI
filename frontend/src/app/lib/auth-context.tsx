"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

type AuthContextType = {
  token: string;
  isLoaded: boolean;
  setToken: (t: string) => void;
  clearToken: () => void;
};

const AuthContext = createContext<AuthContextType>({
  token: "",
  isLoaded: false,
  setToken: () => {},
  clearToken: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState("");
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("armorscan_token") || "";
    setTokenState(stored);
    setIsLoaded(true);
  }, []);

  function setToken(t: string) {
    window.localStorage.setItem("armorscan_token", t);
    setTokenState(t);
  }

  function clearToken() {
    window.localStorage.removeItem("armorscan_token");
    setTokenState("");
  }

  return (
    <AuthContext.Provider value={{ token, isLoaded, setToken, clearToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}