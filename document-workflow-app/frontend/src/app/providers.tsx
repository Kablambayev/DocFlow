import { ConfigProvider, theme } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMemo } from "react";
import type { PropsWithChildren } from "react";

export const AppProviders = ({ children }: PropsWithChildren) => {
  const queryClient = useMemo(() => new QueryClient(), []);

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#0a6e6e",
          borderRadius: 10,
        },
      }}
    >
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ConfigProvider>
  );
};
