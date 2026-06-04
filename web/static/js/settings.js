document.addEventListener('DOMContentLoaded', function() {
    initModals();

    const createBtn = document.getElementById('createBackupBtn');
    const listBtn = document.getElementById('listBackupsBtn');
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const backupItems = document.getElementById('backupItems');

    if (createBtn) {
        createBtn.addEventListener('click', function() {
            createBackup();
        });
    }

    if (listBtn) {
        listBtn.addEventListener('click', function() {
            listBackups();
        });
    }

    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', function() {
            exportData('excel');
        });
    }

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            exportData('csv');
        });
    }

    if (backupItems) {
        backupItems.addEventListener('click', function(event) {
            const target = event.target.closest('.backup-restore-btn');
            if (!target) return;
            const filename = target.getAttribute('data-filename');
            if (filename) {
                restoreBackup(filename);
            }
        });
    }
});

async function createBackup() {
    const comment = prompt('Введите комментарий для резервной копии (необязательно):', '');

    try {
        const result = await makeRequest('/api/backup', {
            method: 'POST',
            body: JSON.stringify({ comment: comment || '' })
        });

        if (result.success) {
            showStatus('Резервная копия успешно создана!', 'success');
        } else {
            showStatus('Ошибка при создании резервной копии: ' + result.message, 'error');
        }
    } catch (error) {
        showStatus('Ошибка сети: ' + error.message, 'error');
    }
}

async function listBackups() {
    try {
        const result = await makeRequest('/api/backups');
        if (result.success) {
            const backupList = document.getElementById('backupList');
            const backupItems = document.getElementById('backupItems');

            if (result.data && result.data.length > 0) {
                let html = '';
                result.data.forEach(backup => {
                    const date = new Date(backup.created_at).toLocaleString('ru-RU');
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">${backup.filename}</h6>
                                    <small class="text-muted">Создано: ${date}</small>
                                    ${backup.comment ? `<p class="mb-0 small">${backup.comment}</p>` : ''}
                                </div>
                                <div>
                                    <small class="text-muted me-2">${backup.size}</small>
                                    <button class="btn btn-sm btn-outline-primary backup-restore-btn" data-filename="${backup.filename}">
                                        <i class="bi bi-arrow-counterclockwise"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });

                backupItems.innerHTML = html;
                backupList.style.display = 'block';
            } else {
                backupItems.innerHTML = '<div class="list-group-item text-center text-muted">Нет резервных копий</div>';
                backupList.style.display = 'block';
            }
        }
    } catch (error) {
        showStatus('Ошибка загрузки списка резервных копий: ' + error.message, 'error');
    }
}

async function restoreBackup(filename) {
    if (confirm(`Вы уверены, что хотите восстановить базу данных из резервной копии "${filename}"?`)) {
        showStatus('Восстановление из резервной копии...', 'info');
        setTimeout(() => {
            showStatus('Функция восстановления находится в разработке', 'warning');
        }, 1000);
    }
}

async function exportData(format) {
    try {
        window.open(`/api/export?format=${format}`, '_blank');
        showStatus(`Экспорт в ${format.toUpperCase()} начат`, 'success');
    } catch (error) {
        showStatus('Ошибка экспорта: ' + error.message, 'error');
    }
}