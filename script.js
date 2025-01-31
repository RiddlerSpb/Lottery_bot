let priceChart;


console.log("Данные от Telegram:", Telegram.WebApp.initDataUnsafe);
// Загрузка данных игрока
async function loadPlayerData() {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user) {
        alert("Ошибка: пользователь не авторизован.");
        return;
    }

    try {
        // Отображаем ник Telegram
        document.getElementById("username").textContent = `👤 ${user.username || "Аноним"}`;

        // Загружаем остальные данные
        const response = await fetch(`/get_player_data?user_id=${user.id}`);
        if (!response.ok) {
            throw new Error("Ошибка при загрузке данных");
        }
        const data = await response.json();

        document.getElementById("balance").textContent = `💰 Баланс: ${data.balance} TNDUSD`;
        document.getElementById("tnd").textContent = `🪙 TND: ${data.portfolio.TND || 0}`;
    } catch (error) {
        console.error("Ошибка:", error);
        alert("Не удалось загрузить данные. Попробуйте позже.");
    }
}

// Загрузка графика цены TND
async function loadPriceChart() {
    const response = await fetch('/get_tnd_price_history');
    const data = await response.json();

    const ctx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(entry => new Date(entry.timestamp * 1000).toLocaleTimeString()),
            datasets: [{
                label: 'Цена TND',
                data: data.map(entry => entry.price),
                borderColor: 'blue',
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Время'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Цена (TNDUSD)'
                    }
                }
            }
        }
    });
}

// Загрузка стакана заявок
async function loadOrderBook() {
    const response = await fetch('/get_order_book');
    const data = await response.json();

    const buyOrders = data.filter(order => order.type === 'buy');
    const sellOrders = data.filter(order => order.type === 'sell');

    document.getElementById('buyOrders').innerHTML = buyOrders.map(order => `
        <div>Купить ${order.amount} TND по ${order.price} TNDUSD</div>
    `).join('');

    document.getElementById('sellOrders').innerHTML = sellOrders.map(order => `
        <div>Продать ${order.amount} TND по ${order.price} TNDUSD</div>
    `).join('');
}

// Покупка TND
async function buyTND() {
    const user = Telegram.WebApp.initDataUnsafe.user;
    const response = await fetch(`/buy_tnd?user_id=${user.id}`);
    const result = await response.json();
    alert(result.message);
    loadPlayerData();
}

// Продажа TND
async function sellTND() {
    const user = Telegram.WebApp.initDataUnsafe.user;
    const response = await fetch(`/sell_tnd?user_id=${user.id}`);
    const result = await response.json();
    alert(result.message);
    loadPlayerData();
}

// Функция для открытия главной страницы
function openMain() {
    document.getElementById("mainPage").style.display = "block";
    document.getElementById("referralPage").style.display = "none";
    document.getElementById("settingsPage").style.display = "none";
}

// Функция для открытия реферальной страницы
function openReferral() {
    document.getElementById("mainPage").style.display = "none";
    document.getElementById("referralPage").style.display = "block";
    document.getElementById("settingsPage").style.display = "none";
    loadReferralData();  // Загружаем данные для реферальной страницы
}

// Функция для открытия страницы настроек
function openSettings() {
    document.getElementById("mainPage").style.display = "none";
    document.getElementById("referralPage").style.display = "none";
    document.getElementById("settingsPage").style.display = "block";
}

// Загружаем данные для реферальной страницы
async function loadPlayerData() {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user) {
        alert("Ошибка: пользователь не авторизован.");
        return;
    }

    try {
        console.log("Запрос данных игрока...");
        const response = await fetch(`/get_player_data?user_id=${user.id}`);
        console.log("Ответ сервера:", response);
        
        if (!response.ok) {
            throw new Error("Ошибка при загрузке данных");
        }
        
        const data = await response.json();
        console.log("Данные игрока:", data);

        // Обновляем интерфейс
        document.getElementById("username").textContent = `👤 ${user.username || "Аноним"}`;
        document.getElementById("balance").textContent = `💰 Баланс: ${data.balance} TNDUSD`;
        document.getElementById("tnd").textContent = `🪙 TND: ${data.portfolio.TND || 0}`;
    } catch (error) {
        console.error("Ошибка:", error);
        alert("Не удалось загрузить данные. Попробуйте позже.");
    }
}

// Инициализация
Telegram.WebApp.ready();
openMain();  // По умолчанию открываем главную страницу
loadPlayerData();
loadPriceChart();
loadOrderBook();