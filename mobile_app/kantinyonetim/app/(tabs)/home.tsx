// mobile_app/kantinyonetim/app/(tabs)/home.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Modal, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FontAwesome } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system';
import LottieView from 'lottie-react-native';
import Toast from 'react-native-toast-message';
import { API_URL } from '@/constants/constants';

// Interfaces
interface OrderSummaryItem {
  menu_item_id: number;
  name: string;
  quantity: number;
  price: string;
}

interface OrderSummary {
  items: OrderSummaryItem[];
  notes: string;
  transcribed_text: string;
}

export default function MainPage() {
    const [isRecording, setIsRecording] = useState(false);
    const [recording, setRecording] = useState<Audio.Recording | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [orderSummary, setOrderSummary] = useState<OrderSummary | null>(null);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [showAnimation, setShowAnimation] = useState(false);
    const router = useRouter();

    useEffect(() => {
      Audio.requestPermissionsAsync();
    }, []);

    async function startRecording() {
      try {
        await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
        const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
        setRecording(recording);
        setIsRecording(true);
      } catch (err) {
        console.error('Ses kaydı başlatılamadı:', err);
        Alert.alert('Hata', 'Mikrofon kaydı başlatılamadı.');
      }
    }

    async function stopRecordingAndParse() {
      setIsRecording(false);
      setIsLoading(true);

      if (!recording) {
        setIsLoading(false);
        return;
      }
      
      try {
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        if (!uri) { throw new Error('Kayıt URI’si bulunamadı.'); }

        const accessToken = await AsyncStorage.getItem('accessToken');
        const response = await FileSystem.uploadAsync(`${API_URL}/parse-voice-order/`, uri, {
            httpMethod: 'POST',
            uploadType: FileSystem.FileSystemUploadType.MULTIPART,
            fieldName: 'audio',
            mimeType: 'audio/m4a',
            headers: { 'Authorization': `Bearer ${accessToken}` },
        });

        const result = JSON.parse(response.body);

        if (response.status === 200) {
            setOrderSummary(result);
            setIsModalVisible(true);
        } else {
            Alert.alert('Hata', result.detail || 'Siparişiniz anlaşılamadı.');
        }
      } catch (error) {
        console.error('Sipariş analizi hatası:', error);
        Alert.alert('Hata', 'Siparişiniz işlenirken bir sorun oluştu.');
      } finally {
        setIsLoading(false);
        setRecording(null);
      }
    }
    
    const handleConfirmOrder = async () => {
        if (!orderSummary) return;
    
        setIsLoading(true);
        
        try {
            const accessToken = await AsyncStorage.getItem('accessToken');
            const response = await fetch(`${API_URL}/confirm-order/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken}` },
                body: JSON.stringify({ items: orderSummary.items, notes: orderSummary.notes }),
            });
    
            const result = await response.json();
            if (response.ok) {
                setShowAnimation(true);
                setTimeout(() => {
                    setIsModalVisible(false);
                    setShowAnimation(false);
                    setOrderSummary(null);
                    Toast.show({ type: 'success', text1: 'Siparişiniz Alındı!', text2: `Sipariş #${result.id} başarıyla oluşturuldu.`});
                    setIsLoading(false);
                }, 2000); 
            } else {
                Alert.alert('Hata', result.detail || 'Sipariş oluşturulamadı.');
                setIsLoading(false);
            }
        } catch (error) {
            Alert.alert('Hata', 'Sipariş onayı sırasında bir sorun oluştu.');
            setIsLoading(false);
        }
    };


    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.title}>Sesli Sipariş</Text>
        
        <TouchableOpacity 
          style={[styles.micButton, isRecording && styles.micButtonRecording]} 
          onPress={isRecording ? stopRecordingAndParse : startRecording}
          disabled={isLoading}>
          {isLoading && !isModalVisible ? (
            <ActivityIndicator color="#fff" size="large" />
          ) : (
            <FontAwesome name="microphone" size={50} color="#fff" />
          )}
        </TouchableOpacity>

        {isRecording && <Text style={styles.recordingText}>Dinleniyor...</Text>}
        
        <Text style={styles.helpText}>Sipariş vermek için mikrofona dokunun.</Text>

        <Modal
            animationType="fade"
            transparent={true}
            visible={isModalVisible}
            onRequestClose={() => {
                if (!showAnimation) setIsModalVisible(false);
            }}
        >
            <View style={styles.modalContainer}>
                <View style={styles.modalView}>
                    {showAnimation ? (
                        <>
                           {/* Lottie animasyonu bul assets/animations klasörü oluşturup checkmark.json dosyasını oraya at */}
                           { <LottieView
                                source={require('@/assets/animations/checkmark.json')}
                                autoPlay
                                loop={false}
                                style={{ width: 150, height: 150 }}
                            /> }
                            <Text style={{fontSize: 24, fontWeight: 'bold', color: '#28a745'}}>Onaylandı!</Text>
                        </>
                    ) : (
                        <>
                            <Text style={styles.modalTitle}>Sipariş Özeti</Text>
                            <Text style={styles.transcribedText}>"{orderSummary?.transcribed_text}"</Text>
                            
                            <FlatList
                                data={orderSummary?.items}
                                style={{width: '100%'}}
                                keyExtractor={(item) => item.menu_item_id.toString()}
                                renderItem={({ item }) => (
                                    <View style={styles.summaryItem}>
                                        <Text style={styles.summaryItemText}>{item.name} (x{item.quantity})</Text>
                                        <Text style={styles.summaryItemText}>₺{(parseFloat(item.price) * item.quantity).toFixed(2)}</Text>
                                    </View>
                                )}
                            />

                            {orderSummary?.notes ? <Text style={styles.notes}>Not: {orderSummary.notes}</Text> : null}
                            
                            <View style={styles.modalButtons}>
                                <TouchableOpacity style={styles.modalButtonCancel} onPress={() => setIsModalVisible(false)}>
                                    <Text style={styles.buttonText}>İptal</Text>
                                </TouchableOpacity>
                                <TouchableOpacity style={styles.modalButtonConfirm} onPress={handleConfirmOrder} disabled={isLoading}>
                                    {isLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Onayla</Text>}
                                </TouchableOpacity>
                            </View>
                        </>
                    )}
                </View>
            </View>
        </Modal>
      </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
        padding: 20,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        marginBottom: 40,
        color: '#333',
    },
    micButton: {
        width: 120,
        height: 120,
        borderRadius: 60,
        backgroundColor: '#2563eb',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 5,
        elevation: 8,
    },
    micButtonRecording: {
      backgroundColor: '#dc2626',
    },
    recordingText: {
      marginTop: 20,
      fontSize: 18,
      fontWeight: 'bold',
      color: '#dc2626',
    },
    orderMessage: {
      marginTop: 20,
      fontSize: 16,
      textAlign: 'center',
      color: '#16a34a',
    },
    helpText: {
      marginTop: 50,
      fontSize: 16,
      color: '#666',
      textAlign: 'center',
    },
    modalContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0,0,0,0.5)',
    },
    modalView: {
        width: '90%',
        maxWidth: 400,
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 24,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
        shadowRadius: 4,
        elevation: 5,
    },
    modalTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 16,
        color: '#111827',
    },
    transcribedText: {
        fontStyle: 'italic',
        color: '#4b5563',
        marginBottom: 20,
        textAlign: 'center',
        fontSize: 16,
    },
    summaryItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        width: '100%',
        paddingVertical: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#e5e7eb',
    },
    summaryItemText: {
        fontSize: 16,
        color: '#374151',
    },
    notes: {
        width: '100%',
        marginTop: 16,
        fontSize: 14,
        fontWeight: '600',
        color: '#1e293b',
        backgroundColor: '#f3f4f6',
        padding: 10,
        borderRadius: 6,
    },
    modalButtons: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        width: '100%',
        marginTop: 24,
    },
    modalButtonCancel: {
        backgroundColor: '#6b7280',
        paddingVertical: 12,
        paddingHorizontal: 24,
        borderRadius: 8,
        flex: 1,
        marginRight: 10,
        alignItems: 'center',
    },
    modalButtonConfirm: {
        backgroundColor: '#2563eb',
        paddingVertical: 12,
        paddingHorizontal: 24,
        borderRadius: 8,
        flex: 1,
        marginLeft: 10,
        alignItems: 'center',
    },
    buttonText: {
        color: 'white',
        fontWeight: 'bold',
        fontSize: 16,
    },
});