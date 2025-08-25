// mobile_app/kantinyonetim/app/(tabs)/profile.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, TouchableOpacity, ActivityIndicator, Button } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { API_URL } from '@/constants/constants';

interface OrderItem {
  id: number;
  menu_item_name: string;
  quantity: number;
}

interface Order {
  id: number;
  status: string;
  total: string;
  created_at: string;
  order_items: OrderItem[];
}

interface UserProfile {
  id: number;
  username: string;
  role: string;
}

export default function ProfileScreen() {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const handleLogout = async () => {
    Alert.alert(
      'Çıkış Yap',
      'Oturumunuzu kapatmak istediğinizden emin misiniz?',
      [
        { text: 'Hayır', style: 'cancel' },
        {
          text: 'Evet',
          onPress: async () => {
            await AsyncStorage.removeItem('accessToken');
            await AsyncStorage.removeItem('refreshToken');
            router.replace('/login');
          },
        },
      ]
    );
  };

  const fetchUserProfile = async () => {
    try {
      const accessToken = await AsyncStorage.getItem('accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }

      const response = await fetch(`${API_URL}/users/me/`, {
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
        const user: UserProfile = await response.json();
        setUserProfile(user);
      } else {
        Alert.alert('Hata', 'Kullanıcı bilgileri yüklenirken bir sorun oluştu.');
      }
    } catch (error) {
      console.error('Kullanıcı bilgisi yükleme hatası:', error);
      Alert.alert('Hata', 'Sunucuya bağlanırken bir sorun oluştu.');
    }
  };

  const fetchOrders = async () => {
    try {
      setIsLoading(true);
      const accessToken = await AsyncStorage.getItem('accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }

      const response = await fetch(`${API_URL}/orders/`, {
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
        const data: Order[] = await response.json();
        setOrders(data);
      } else {
        Alert.alert('Hata', 'Siparişler yüklenirken bir sorun oluştu.');
      }
    } catch (error) {
      console.error('Sipariş yükleme hatası:', error);
      Alert.alert('Hata', 'Sunucuya bağlanırken bir sorun oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelOrder = async (orderId: number) => {
    Alert.alert(
      'Siparişi İptal Et',
      'Bu siparişi iptal etmek istediğinizden emin misiniz?',
      [
        { text: 'Hayır', style: 'cancel' },
        {
          text: 'Evet',
          onPress: async () => {
            try {
              const accessToken = await AsyncStorage.getItem('accessToken');
              if (!accessToken) {
                router.replace('/login');
                return;
              }

              const response = await fetch(`${API_URL}/orders/${orderId}/cancel/`, {
                method: 'POST',
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
                Alert.alert('Başarılı', 'Sipariş başarıyla iptal edildi.');
                fetchOrders(); 
              } else {
                const errorData = await response.json();
                Alert.alert('Hata', errorData.detail || 'Sipariş iptal edilemedi.');
              }
            } catch (error) {
              console.error('Sipariş iptal hatası:', error);
              Alert.alert('Hata', 'Sipariş iptal edilirken bir sorun oluştu.');
            }
          },
        },
      ]
    );
  };

  useEffect(() => {
    fetchUserProfile();
    fetchOrders();
  }, []);

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'pending': return styles.pendingStatus;
      case 'preparing': return styles.preparingStatus;
      case 'ready': return styles.readyStatus;
      case 'completed': return styles.completedStatus;
      case 'cancelled': return styles.cancelledStatus;
      default: return null;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Profil ve Siparişlerim</Text>
      
      <View style={styles.profileCard}>
        {userProfile ? (
          <>
            <Text style={styles.profileText}>Kullanıcı Adı: {userProfile.username}</Text>
            <Text style={styles.profileText}>Rol: {userProfile.role}</Text>
            <Button title="Çıkış Yap" onPress={handleLogout} />
          </>
        ) : (
          <ActivityIndicator size="small" />
        )}
      </View>

      <Text style={styles.subTitle}>Sipariş Geçmişim</Text>
      
      {isLoading ? (
        <ActivityIndicator size="large" color="#0000ff" />
      ) : (
        <ScrollView style={styles.orderList}>
          {orders.length > 0 ? (
            orders.map((order: Order) => (
              <View key={order.id} style={styles.orderCard}>
                <View style={styles.orderHeader}>
                  <Text style={styles.orderId}>Sipariş #{order.id}</Text>
                  <Text style={[styles.statusBadge, getStatusStyle(order.status)]}>{order.status}</Text>
                </View>
                <Text style={styles.orderTotal}>Toplam: ₺{order.total}</Text>
                <Text style={styles.orderDate}>Tarih: {new Date(order.created_at).toLocaleString('tr-TR')}</Text>
                <View style={styles.orderItems}>
                  {order.order_items.map((item: OrderItem) => (
                    <Text key={item.id} style={styles.orderItem}>
                      - {item.menu_item_name} (x{item.quantity})
                    </Text>
                  ))}
                </View>
                {(order.status === 'pending' || order.status === 'preparing') && (
                  <TouchableOpacity
                    style={styles.cancelButton}
                    onPress={() => handleCancelOrder(order.id)}
                  >
                    <Text style={styles.cancelButtonText}>İptal Et</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))
          ) : (
            <Text style={styles.noOrdersText}>Henüz siparişiniz bulunmamaktadır.</Text>
          )}
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
    marginBottom: 10,
    textAlign: 'center',
  },
  subTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginVertical: 15,
    textAlign: 'center',
  },
  profileCard: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  profileText: {
    fontSize: 16,
    marginBottom: 5,
  },
  orderList: {
    width: '100%',
  },
  orderCard: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  orderId: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  orderTotal: {
    fontSize: 16,
    color: '#333',
    marginBottom: 5,
  },
  orderDate: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  orderItems: {
    marginBottom: 10,
  },
  orderItem: {
    fontSize: 14,
    color: '#555',
  },
  cancelButton: {
    backgroundColor: '#dc3545',
    padding: 10,
    borderRadius: 5,
    alignItems: 'center',
    marginTop: 10,
  },
  cancelButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  statusBadge: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  pendingStatus: { backgroundColor: '#ffc107' },
  preparingStatus: { backgroundColor: '#17a2b8' },
  readyStatus: { backgroundColor: '#28a745' },
  completedStatus: { backgroundColor: '#007bff' },
  cancelledStatus: { backgroundColor: '#dc3545' },
  noOrdersText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
    color: '#666',
  },
});
