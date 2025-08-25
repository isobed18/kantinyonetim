// mobile_app/kantinyonetim/app/(tabs)/staff.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { API_URL } from '@/constants/constants';

interface OrderItem {
  id: number;
  menu_item_name: string;
  quantity: number;
  line_total: string;
  price_at_order_time: string;
}

interface Order {
  id: number;
  status: string;
  total: string;
  user_username: string;
  order_items: OrderItem[];
  created_at: string;
}

export default function StaffPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

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
        setOrders(data.filter(o => o.status === 'pending' || o.status === 'preparing' || o.status === 'ready'));
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

  const handleUpdateStatus = async (orderId: number, newStatus: string) => {
    try {
      const accessToken = await AsyncStorage.getItem('accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }

      const response = await fetch(`${API_URL}/orders/${orderId}/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.status === 401) {
        Alert.alert('Oturum Süresi Doldu', 'Lütfen tekrar giriş yapın.');
        await AsyncStorage.removeItem('accessToken');
        router.replace('/login');
        return;
      }

      if (response.ok) {
        Alert.alert('Başarılı', `Sipariş #${orderId} durumu güncellendi: ${newStatus}`);
        fetchOrders(); 
      } else {
        const errorData = await response.json();
        Alert.alert('Hata', errorData.detail || 'Sipariş durumu güncellenemedi.');
      }
    } catch (error) {
      console.error('Sipariş durum güncelleme hatası:', error);
      Alert.alert('Hata', 'Sipariş durumu güncellenirken bir sorun oluştu.');
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
              if (response.ok) {
                Alert.alert('Başarılı', `Sipariş #${orderId} iptal edildi.`);
                fetchOrders();
              } else {
                const errorData = await response.json();
                Alert.alert('Hata', errorData.detail || 'Sipariş iptal edilemedi.');
              }
            } catch (error) {
              Alert.alert('Hata', 'Sipariş iptal edilirken bir sorun oluştu.');
            }
          },
        },
      ]
    );
  };

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(() => {
      fetchOrders();
    }, 10000); 
    return () => clearInterval(interval);
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
      <Text style={styles.title}>Sipariş Yönetimi</Text>
      {isLoading ? (
        <ActivityIndicator size="large" color="#0000ff" />
      ) : (
        <ScrollView style={styles.orderList}>
          {orders.length > 0 ? (
            orders.map((order: Order) => (
              <View key={order.id} style={styles.orderCard}>
                <Text style={styles.orderId}>Sipariş #{order.id} ({order.user_username})</Text>
                <Text style={styles.orderDate}>Tarih: {new Date(order.created_at).toLocaleString('tr-TR')}</Text>
                <View style={styles.orderItems}>
                  {order.order_items.map((item: OrderItem) => (
                    <Text key={item.id} style={styles.orderItem}>
                      - {item.menu_item_name} (x{item.quantity}) - Toplam: ₺{item.line_total}
                    </Text>
                  ))}
                </View>
                <Text style={styles.orderTotal}>Toplam Fiyat: ₺{order.total}</Text> 
                <View style={styles.buttonContainer}>
                  <TouchableOpacity
                    style={styles.deliveredButton}
                    onPress={() => handleUpdateStatus(order.id, 'completed')}
                  >
                    <Text style={styles.buttonText}>Teslim Et</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.cancelButton}
                    onPress={() => handleCancelOrder(order.id)}
                  >
                    <Text style={styles.buttonText}>İptal Et</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          ) : (
            <Text style={styles.noOrdersText}>Henüz aktif sipariş bulunmamaktadır.</Text>
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
    marginBottom: 20,
    textAlign: 'center',
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
  orderId: {
    fontSize: 18,
    fontWeight: 'bold',
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
  orderTotal: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#28a745',
    marginTop: 5,
    textAlign: 'right',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  deliveredButton: {
    backgroundColor: '#28a745',
    padding: 10,
    borderRadius: 5,
    alignItems: 'center',
    flex: 1,
    marginRight: 5,
  },
  cancelButton: {
    backgroundColor: '#dc3545',
    padding: 10,
    borderRadius: 5,
    alignItems: 'center',
    flex: 1,
    marginLeft: 5,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  noOrdersText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
    color: '#666',
  },
  pendingStatus: { backgroundColor: '#ffc107' },
  preparingStatus: { backgroundColor: '#17a2b8' },
  readyStatus: { backgroundColor: '#28a745' },
  completedStatus: { backgroundColor: '#007bff' },
  cancelledStatus: { backgroundColor: '#dc3545' },
});