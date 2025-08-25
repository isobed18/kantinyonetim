// mobile_app/kantinyonetim/app/_layout.tsx
import { Stack } from 'expo-router';

// Bu, uygulamanın temel Stack navigasyonunu yöneten dosyadır.
export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
    </Stack>
  );
}
