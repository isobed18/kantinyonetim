// mobile_app/kantinyonetim/app/_layout.tsx

import { Stack } from 'expo-router';
import Toast from 'react-native-toast-message';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StyleSheet } from 'react-native';

export default function RootLayout() {
  return (
    // gesture handler ile sarmaladık
    <GestureHandlerRootView style={styles.container}>
      <>
        {/* toastı kaldırdım bozuk. sayfa geçişi yok */}
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="login" />
          <Stack.Screen name="(tabs)" />
        </Stack>
        {/* compenent toast mesajları için kalmalı*/}
        <Toast />
      </>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});