// mobile_app/kantinyonetim/app/(tabs)/home.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FontAwesome } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system';
import { API_URL } from '@/constants/constants';

export default function MainPage() {
    const [isRecording, setIsRecording] = useState(false);
    const [recording, setRecording] = useState<Audio.Recording | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [orderMessage, setOrderMessage] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
      (async () => {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert('İzin Reddedildi', 'Sesli sipariş için mikrofon izni gereklidir.');
        }
      })();
    }, []);

    async function startRecording() {
      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
        console.log('Ses kaydı başlıyor...');
        const newRecording = new Audio.Recording();
        await newRecording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
        await newRecording.startAsync();
        setRecording(newRecording);
        setIsRecording(true);
      } catch (err) {
        console.error('Ses kaydı başlatılamadı:', err);
        Alert.alert('Hata', 'Ses kaydı başlatılamadı.');
      }
    }

    async function stopRecordingAndSend() {
      console.log('Ses kaydı durduruluyor...');
      setIsRecording(false);
      setIsLoading(true);

      if (!recording) {
        Alert.alert('Hata', 'Kayıt bulunamadı.');
        setIsLoading(false);
        return;
      }
      
      try {
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        console.log('Ses kaydı tamamlandı, URI:', uri);

        if (!uri) {
          Alert.alert('Hata', 'Kayıt URI’si bulunamadı.');
          setIsLoading(false);
          return;
        }

        const accessToken = await AsyncStorage.getItem('accessToken');
        if (!accessToken) {
          Alert.alert('Yetkilendirme Hatası', 'Lütfen tekrar giriş yapın.');
          router.replace('/login');
          return;
        }

        const response = await FileSystem.uploadAsync(
          `${API_URL}/voice-order/`,
          uri,
          {
            httpMethod: 'POST',
            uploadType: FileSystem.FileSystemUploadType.MULTIPART,
            fieldName: 'audio',
            mimeType: 'audio/m4a',
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          }
        );

        if (response.status === 401) {
            Alert.alert('Oturum Süresi Doldu', 'Lütfen tekrar giriş yapın.');
            router.replace('/login');
            await AsyncStorage.removeItem('accessToken');
            await AsyncStorage.removeItem('refreshToken');
            return;
        }
        
        const result = JSON.parse(response.body);

        if (response.status === 201) {
          setOrderMessage(`Sipariş başarıyla alındı! Sipariş ID: ${result.order_id}`);
          Alert.alert('Sipariş Alındı', `Transkripsiyon: "${result.transcribed_text}"`);
        } else {
          Alert.alert('Hata', result.detail || 'Sesli sipariş oluşturulurken bir hata oluştu.');
        }
      } catch (error) {
        console.error('API çağrısı hatası:', error);
        Alert.alert('Hata', 'Sunucuya istek gönderilirken bir sorun oluştu.');
      } finally {
        setIsLoading(false);
        setRecording(null);
      }
    }

    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.title}>Sesli Sipariş</Text>
        
        <TouchableOpacity 
          style={[styles.micButton, isRecording && styles.micButtonRecording]} 
          onPress={isRecording ? stopRecordingAndSend : startRecording}
          disabled={isLoading}>
          {isLoading ? (
            <ActivityIndicator color="#fff" size="large" />
          ) : (
            <FontAwesome name="microphone" size={50} color="#fff" />
          )}
        </TouchableOpacity>

        {isRecording && <Text style={styles.recordingText}>Dinleniyor...</Text>}
        {orderMessage && <Text style={styles.orderMessage}>{orderMessage}</Text>}

        <Text style={styles.helpText}>Mikrofon düğmesine basın ve siparişinizi söyleyin.</Text>
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
});
