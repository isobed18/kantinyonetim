// mobile_app/kantinyonetim/app/(tabs)/_layout.tsx
import React, { useState, useEffect } from 'react';
import { Tabs, Redirect } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { Colors } from '@/constants/Colors';
import { useColorScheme } from '@/hooks/useColorScheme';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { API_URL } from '@/constants/constants';

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserRole = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('accessToken');
        if (!accessToken) {
          setUserRole(null);
          return;
        }

        const response = await fetch(`${API_URL}/users/me/`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });

        if (response.status === 401) {
          await AsyncStorage.removeItem('accessToken');
          await AsyncStorage.removeItem('refreshToken');
          setUserRole(null);
        } else if (response.ok) {
          const user = await response.json();
          setUserRole(user.role);
        } else {
          setUserRole(null);
        }
      } catch (error) {
        console.error('Kullanıcı rolü alınırken hata:', error);
        setUserRole(null);
      }
    };
    fetchUserRole();
  }, []);

  if (userRole === null) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!userRole) {
      return <Redirect href="/login" />;
  }
  
  // Navbar'da hangi sayfanın aktif olduğunu daha net göstermek için tabBarIcon stilini düzenledik
  const getTabBarIcon = (name: React.ComponentProps<typeof FontAwesome>['name'], focused: boolean, color: string) => {
    return <FontAwesome name={name} color={color} size={24} />;
  };

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false, // Sayfa başlıklarını gizledik
        tabBarStyle: {
          backgroundColor: Colors[colorScheme ?? 'light'].background,
          borderTopColor: Colors[colorScheme ?? 'light'].text,
        },
      }}>

      {/* Personel ve Yönetici için Sekmeler */}
      {(userRole === 'staff' || userRole === 'admin') && (
        <>
          <Tabs.Screen
            name="staff"
            options={{
              title: 'Sipariş Yönetimi',
              tabBarIcon: ({ color, focused }) => getTabBarIcon('list-ul', focused, color),
            }}
          />
          <Tabs.Screen
            name="profile"
            options={{
              title: 'Profil',
              tabBarIcon: ({ color, focused }) => getTabBarIcon('user', focused, color),
            }}
          />
        </>
      )}

      {/* Müşteri için Sekmeler */}
      {userRole === 'customer' && (
        <>
          <Tabs.Screen
            name="home"
            options={{
              title: 'Sesli Sipariş',
              tabBarIcon: ({ color, focused }) => getTabBarIcon('microphone', focused, color),
            }}
          />
          <Tabs.Screen
            name="menu"
            options={{
              title: 'Menü',
              tabBarIcon: ({ color, focused }) => getTabBarIcon('cutlery', focused, color),
            }}
          />
          <Tabs.Screen
            name="profile"
            options={{
              title: 'Profil',
              tabBarIcon: ({ color, focused }) => getTabBarIcon('user', focused, color),
            }}
          />
        </>
      )}
    </Tabs>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
