// mobile_app/kantinyonetim/app/index.tsx
import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect } from 'expo-router';

// Bu dosya, uygulamanın başlangıç noktasıdır ve kimlik doğrulama durumunu kontrol eder.
export default function AppEntry() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // Uygulama yüklendiğinde, AsyncStorage'den bir token olup olmadığını kontrol et.
    const checkAuthStatus = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('accessToken');
        setIsAuthenticated(!!accessToken);
      } catch (e) {
        console.error("Token okunurken hata oluştu:", e);
        setIsAuthenticated(false); // Hata durumunda giriş yapılmamış say
      }
    };
    checkAuthStatus();
  }, []);

  // Kimlik doğrulama durumu hala kontrol ediliyorsa, bir yükleme göstergesi sun.
  if (isAuthenticated === null) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  // Kullanıcı giriş yapmamışsa, login sayfasına yönlendir.
  if (!isAuthenticated) {
    return <Redirect href="/login" />;
  }

  // Kullanıcı giriş yapmışsa, ana sekme düzenine yönlendir.
  return <Redirect href="/(tabs)/home" />;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
