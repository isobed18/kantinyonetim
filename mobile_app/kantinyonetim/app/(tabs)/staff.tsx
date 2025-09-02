// mobile_app/kantinyonetim/app/(tabs)/staff.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, FlatList, Alert, TouchableOpacity,
  ActivityIndicator, RefreshControl, Animated
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { API_URL } from '@/constants/constants';
import { Swipeable } from 'react-native-gesture-handler';
import { FontAwesome } from '@expo/vector-icons';
import Toast from 'react-native-toast-message';

interface OrderItem {
  id: number;
  menu_item_name: string;
  quantity: number;
  line_total: string;
}

interface Order {
  id: number;
  status: string;
  total: string;
  user_username: string;
  order_items: OrderItem[];
  created_at: string;
  notes?: string;
}

//  KAYDIRMA ANİMASYONU COMPONENTLERİ
const AnimatedIcon = Animated.createAnimatedComponent(FontAwesome);

const renderSwipeAction = (
  text: string,
  color: string,
  iconName: React.ComponentProps<typeof FontAwesome>['name'],
  x: number,
  progress: Animated.AnimatedInterpolation<number>
) => {
  const trans = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [x, 0],
    extrapolate: 'clamp',
  });

  const scale = progress.interpolate({
    inputRange: [0, 0.1, 1],
    outputRange: [0.1, 1, 1],
     extrapolate: 'clamp',
  });

  return (
    <Animated.View style={{ flex: 1, transform: [{ translateX: trans }] }}>
      <TouchableOpacity
        style={[styles.swipeAction, { backgroundColor: color }]}
      >
        <AnimatedIcon name={iconName} size={24} color="white" style={{ transform: [{ scale }] }}/>
        <Animated.Text style={[styles.swipeActionText, { transform: [{ scale }] }]}>{text}</Animated.Text>
      </TouchableOpacity>
    </Animated.View>
  );
};

// MAIN COMPONENT
export default function StaffPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);
  const swipeableRefs = useRef<{ [key: number]: Swipeable | null }>({});

  const fetchOrders = async (isRefreshing = false) => {
    if (!isRefreshing) setIsLoading(true);
    try {
      const accessToken = await AsyncStorage.getItem('accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }

      const response = await fetch(`${API_URL}/orders/`, {
        headers: { 'Authorization': `Bearer ${accessToken}` },
      });

      if (response.status === 401) {
        Toast.show({ type: 'error', text1: 'Oturum Süresi Doldu', text2: 'Lütfen tekrar giriş yapın.' });
        await AsyncStorage.clear();
        router.replace('/login');
        return;
      }

      if (response.ok) {
        const data: Order[] = await response.json();
        setOrders(data.filter(o => ['pending', 'preparing', 'ready'].includes(o.status)));
      } else {
        Toast.show({ type: 'error', text1: 'Hata', text2: 'Siparişler yüklenirken bir sorun oluştu.' });
      }
    } catch (error) {
      console.error('Sipariş yükleme hatası:', error);
      Toast.show({ type: 'error', text1: 'Hata', text2: 'Sunucuya bağlanırken bir sorun oluştu.' });
    } finally {
      if (!isRefreshing) setIsLoading(false);
    }
  };

  const handleUpdateStatus = async (orderId: number, newStatus: string) => {
    swipeableRefs.current[orderId]?.close();
    try {
      const accessToken = await AsyncStorage.getItem('accessToken');
      const response = await fetch(`${API_URL}/orders/${orderId}/`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        Toast.show({ type: 'success', text1: 'Başarılı', text2: `Sipariş #${orderId} teslim edildi.` });
        setOrders(prev => prev.filter(o => o.id !== orderId));
      } else {
        const errorData = await response.json();
        Toast.show({ type: 'error', text1: 'Hata', text2: errorData.detail || 'Durum güncellenemedi.' });
      }
    } catch (error) {
      Toast.show({ type: 'error', text1: 'Hata', text2: 'İşlem sırasında bir sorun oluştu.' });
    }
  };

  const handleCancelOrder = (orderId: number) => {
    swipeableRefs.current[orderId]?.close();
    Alert.alert(
      'Siparişi İptal Et',
      `#${orderId} numaralı siparişi iptal etmek istediğinizden emin misiniz? Bu işlem geri alınamaz.`,
      [
        { text: 'Vazgeç', style: 'cancel' },
        {
          text: 'Evet, İptal Et',
          style: 'destructive',
          onPress: async () => {
            try {
              const accessToken = await AsyncStorage.getItem('accessToken');
              const response = await fetch(`${API_URL}/orders/${orderId}/cancel/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}` },
              });
              if (response.ok) {
                Toast.show({ type: 'info', text1: 'İptal Edildi', text2: `Sipariş #${orderId} iptal edildi.` });
                setOrders(prev => prev.filter(o => o.id !== orderId));
              } else {
                const errorData = await response.json();
                Toast.show({ type: 'error', text1: 'Hata', text2: errorData.detail || 'Sipariş iptal edilemedi.' });
              }
            } catch (error) {
              Toast.show({ type: 'error', text1: 'Hata', text2: 'İşlem sırasında bir sorun oluştu.' });
            }
          },
        },
      ]
    );
  };
  
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchOrders(true);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(() => fetchOrders(true), 15000); 
    return () => clearInterval(interval);
  }, []);

  const getStatusInfo = (status: string): { text: string, style: object } => {
    switch (status) {
      case 'pending': return { text: 'Bekliyor', style: styles.pendingStatus };
      case 'preparing': return { text: 'Hazırlanıyor', style: styles.preparingStatus };
      case 'ready': return { text: 'Hazır', style: styles.readyStatus };
      default: return { text: status, style: {} };
    }
  };

  const renderOrderItem = ({ item }: { item: OrderItem }) => (
    <View style={styles.orderItem}>
        <Text style={styles.orderItemText}>{item.quantity}x {item.menu_item_name}</Text>
        <Text style={styles.orderItemText}>₺{item.line_total}</Text>
    </View>
  );

  const renderOrderCard = ({ item }: { item: Order }) => {
    const statusInfo = getStatusInfo(item.status);
    return (
        <Swipeable
        ref={(ref) => { // 
                    swipeableRefs.current[item.id] = ref;
                }}
            renderLeftActions={(progress, dragX) => 
                <View style={{ width: 90, flexDirection: 'row' }}>
                    {renderSwipeAction('Teslim Et', '#28a745', 'check', -90, progress)}
                </View>
            }
            onSwipeableOpen={(direction) => {
                if (direction === 'left') {
                    handleUpdateStatus(item.id, 'completed');
                } else if (direction === 'right') {
                    handleCancelOrder(item.id);
                }
            }}
            renderRightActions={(progress, dragX) => 
                <View style={{ width: 90, flexDirection: 'row' }}>
                    {renderSwipeAction('İptal', '#dc3545', 'trash', 90, progress)}
                </View>
            }
            overshootFriction={8}
        >
            <View style={styles.orderCard}>
                <View style={styles.orderHeader}>
                    <Text style={styles.orderId}>Sipariş #{item.id} - {item.user_username}</Text>
                    <View style={[styles.statusBadge, statusInfo.style]}>
                        <Text style={styles.statusText}>{statusInfo.text}</Text>
                    </View>
                </View>

                <FlatList
                    data={item.order_items}
                    keyExtractor={(orderItem) => orderItem.id.toString()}
                    renderItem={renderOrderItem}
                    scrollEnabled={false}
                />

                {item.notes ? <Text style={styles.orderNotes}>Not: {item.notes}</Text> : null}
                
                <View style={styles.orderFooter}>
                    <Text style={styles.orderDate}>{new Date(item.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}</Text>
                    <Text style={styles.orderTotal}>Toplam: ₺{item.total}</Text>
                </View>
            </View>
      </Swipeable>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Aktif Siparişler</Text>
      {isLoading && !refreshing ? (
        <ActivityIndicator size="large" color="#2563eb" style={{ flex: 1 }} />
      ) : (
        <FlatList
            data={orders}
            renderItem={renderOrderCard}
            keyExtractor={item => item.id.toString()}
            style={styles.orderList}
            contentContainerStyle={{ paddingBottom: 20 }}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#2563eb"]} tintColor={"#2563eb"} />}
            ListEmptyComponent={<Text style={styles.noOrdersText}>Henüz aktif sipariş bulunmamaktadır.</Text>}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: '#f3f4f6',
    },
    title: {
      fontSize: 28,
      fontWeight: 'bold',
      color: '#111827',
      paddingTop: 20,
      paddingBottom: 20,
      paddingHorizontal: 16,
      textAlign: 'center',
      backgroundColor: 'white',
    },
    orderList: {
      width: '100%',
    },
    orderCard: {
      backgroundColor: 'white',
      marginHorizontal: 16,
      marginVertical: 8,
      borderRadius: 12,
      padding: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08,
      shadowRadius: 8,
      elevation: 5,
    },
    orderHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 12,
      borderBottomWidth: 1,
      borderBottomColor: '#f3f4f6',
      paddingBottom: 12,
    },
    orderId: {
      fontSize: 18,
      fontWeight: 'bold',
      color: '#1f2937',
    },
    statusBadge: {
      paddingVertical: 4,
      paddingHorizontal: 10,
      borderRadius: 12,
    },
    statusText: {
      color: 'white',
      fontWeight: 'bold',
      fontSize: 12,
    },
    orderItem: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingVertical: 4,
    },
    orderItemText: {
      fontSize: 15,
      color: '#4b5563',
    },
    orderNotes: {
      fontSize: 14,
      fontStyle: 'italic',
      color: '#374151',
      marginTop: 12,
      backgroundColor: '#f9fafb',
      padding: 10,
      borderRadius: 6,
      borderWidth: 1,
      borderColor: '#e5e7eb'
    },
    orderFooter: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: 12,
      paddingTop: 12,
      borderTopWidth: 1,
      borderTopColor: '#f3f4f6',
    },
    orderDate: {
      fontSize: 14,
      color: '#6b7280',
    },
    orderTotal: {
      fontSize: 18,
      fontWeight: 'bold',
      color: '#166534',
    },
    noOrdersText: {
      textAlign: 'center',
      marginTop: 50,
      fontSize: 16,
      color: '#6b7280',
    },
    swipeAction: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      width: 90,
    },
    swipeActionText: {
      color: 'white',
      fontWeight: '600',
      fontSize: 14,
      marginTop: 4,
    },
    pendingStatus: { backgroundColor: '#f59e0b' },
    preparingStatus: { backgroundColor: '#3b82f6' },
    readyStatus: { backgroundColor: '#10b981' },
});