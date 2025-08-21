// mobile_app/kantinyonetim/app/(tabs)/_layout.tsx
import React from 'react';
import { Tabs } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { Colors } from '@/constants/Colors';
import { useColorScheme } from '@/hooks/useColorScheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
      }}>
      <Tabs.Screen
        name="home"
        options={{
          title: 'Sipariş Ver',
          tabBarIcon: ({ color, focused }) => (
            <FontAwesome name={focused ? 'microphone' : 'microphone'} color={color} size={24} />
          ),
        }}
      />
    </Tabs>
  );
}
