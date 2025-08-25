// mobile_app/kantinyonetim/app/(tabs)/menu.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, Alert, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { API_URL, BASE_URL } from '@/constants/constants';

interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: string;
  is_available: boolean;
  category: string;
  image: string;
}

export default function MenuScreen() {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchMenuItems = async () => {
    try {
      setIsLoading(true);
      const accessToken = await AsyncStorage.getItem('accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }

      const response = await fetch(`${API_URL}/menu-items/`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.status === 401) {
        Alert.alert('Oturum Süresi Doldu', 'Lütfen tekrar giriş yapın.');
        await AsyncStorage.removeItem('accessToken');
        router.replace('/login');
        return;
      }

      if (response.ok) {
        const data: MenuItem[] = await response.json();
        setMenuItems(data);
      } else {
        Alert.alert('Hata', 'Menü öğeleri yüklenirken bir sorun oluştu.');
      }
    } catch (error) {
      console.error('Menü yükleme hatası:', error);
      Alert.alert('Hata', 'Sunucuya bağlanırken bir sorun oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMenuItems();
  }, []);

  const getCategorizedItems = () => {
    const categories: { [key: string]: MenuItem[] } = {};
    menuItems.forEach(item => {
      if (!categories[item.category]) {
        categories[item.category] = [];
      }
      categories[item.category].push(item);
    });
    return categories;
  };

  const categorizedItems = getCategorizedItems();

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Menü</Text>
      {isLoading ? (
        <ActivityIndicator size="large" color="#0000ff" />
      ) : (
        <ScrollView style={styles.menuList}>
          {Object.keys(categorizedItems).map(category => (
            <View key={category} style={styles.categoryContainer}>
              <Text style={styles.categoryTitle}>{category.replace(/_/g, ' ').toUpperCase()}</Text>
              {categorizedItems[category].map(item => (
                <View key={item.id} style={styles.menuItemCard}>
                  {item.image && (
                    <Image
                      source={{ uri: `${BASE_URL}${item.image}` }}
                      style={styles.menuItemImage}
                    />
                  )}
                  <View style={styles.itemDetails}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <Text style={styles.itemDescription}>{item.description}</Text>
                    <Text style={styles.itemPrice}>₺{item.price}</Text>
                  </View>
                </View>
              ))}
            </View>
          ))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  menuList: {
    width: '100%',
  },
  categoryContainer: {
    marginBottom: 20,
  },
  categoryTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  menuItemCard: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  menuItemImage: {
    width: 80,
    height: 80,
    borderRadius: 5,
    marginRight: 10,
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  itemDescription: {
    fontSize: 14,
    color: '#666',
  },
  itemPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#28a745',
    marginTop: 5,
  },
});