// mobile_app/kantinyonetim/app/_layout.tsx
import { Stack } from 'expo-router';

// Bu, uygulamanın temel Stack navigasyonunu yöneten dosyadır.
// Anasayfa (index.tsx) ilk ekran olarak davranır ve tüm yönlendirme mantığını yönetir.
export default function RootLayout() {
  return (
    <Stack>
      {/* login ve (tabs) rotaları burada tanımlanmıştır. */}
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      {/* index.tsx'i özel olarak Stack'e eklememize gerek yok,
          çünkü o zaten kök dizin olarak varsayılır. */}
    </Stack>
  );
}
